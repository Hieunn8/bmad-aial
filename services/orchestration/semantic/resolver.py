"""Hybrid semantic resolver for governed chat queries."""

from __future__ import annotations

import math
import os
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import httpx
from embedding.client import DIMS, _hash_embed

from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.time_parser import ParsedTimeFilter, parse_time_expression

_AUTO_SELECT_THRESHOLD = 0.62
_AMBIGUITY_DELTA = 0.08
_MIN_CANDIDATE_SCORE = 0.18


@dataclass(frozen=True)
class SemanticPlannerOutput:
    status: str
    selected_term: str | None
    intent: str
    time_filter: dict[str, Any] | None
    dimensions: list[str]
    confidence: float
    needs_clarification: bool
    clarification_question: str | None
    rationale: str
    # Specific dimension value filters, e.g. {"REGION_CODE": "HCM", "CHANNEL_CODE": "ONLINE"}
    entity_filters: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_term": self.selected_term,
            "intent": self.intent,
            "time_filter": self.time_filter,
            "dimensions": list(self.dimensions),
            "entity_filters": dict(self.entity_filters),
            "confidence": round(self.confidence, 4),
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class SemanticResolveCandidate:
    metric: dict[str, Any]
    lexical_score: float
    vector_score: float
    merged_score: float
    rerank_score: float
    validation_errors: list[str] = field(default_factory=list)
    filtered_reason: str | None = None

    @property
    def final_score(self) -> float:
        if self.validation_errors or self.filtered_reason:
            return 0.0
        return self.rerank_score

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "term": str(self.metric.get("term", "")),
            "version_id": str(self.metric.get("active_version_id") or self.metric.get("version_id") or ""),
            "lexical_score": round(self.lexical_score, 4),
            "vector_score": round(self.vector_score, 4),
            "merged_score": round(self.merged_score, 4),
            "rerank_score": round(self.rerank_score, 4),
            "validation_errors": list(self.validation_errors),
            "filtered_reason": self.filtered_reason,
        }


@dataclass(frozen=True)
class SemanticResolveDecision:
    status: str
    semantic_context: list[dict[str, Any]]
    selected: SemanticResolveCandidate | None
    candidates: list[SemanticResolveCandidate]
    normalized_query: str
    confidence: float
    reasons: list[str]
    planner_output: SemanticPlannerOutput | None = None

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "normalized_query": self.normalized_query,
            "confidence": round(self.confidence, 4),
            "selected": self.selected.to_audit_dict() if self.selected else None,
            "candidates": [candidate.to_audit_dict() for candidate in self.candidates],
            "reasons": list(self.reasons),
            "planner_output": self.planner_output.to_dict() if self.planner_output else None,
        }


class SemanticResolver:
    """Resolve free-form Vietnamese chat text to published semantic items.

    The resolver uses lexical/fuzzy matching and deterministic local vectors for
    offline reproducibility. The scoring and audit contract match the production
    path, where the same retrieval_text can be indexed in Weaviate or pgvector.
    """

    def resolve(
        self,
        *,
        query: str,
        metrics: list[dict[str, Any]],
        principal: JWTClaims | None = None,
        allowed_terms: set[str] | None = None,
        top_k: int = 5,
    ) -> SemanticResolveDecision:
        normalized_query = normalize_semantic_text(query)
        if not normalized_query:
            return SemanticResolveDecision(
                status="no_match",
                semantic_context=[],
                selected=None,
                candidates=[],
                normalized_query="",
                confidence=0.0,
                reasons=["empty_query"],
            )

        scored: list[SemanticResolveCandidate] = []
        for metric in metrics:
            filtered_reason = _security_filter_reason(metric, principal=principal, allowed_terms=allowed_terms)
            validation_errors = _validate_metric(metric)
            lexical_score = _lexical_score(normalized_query, metric)
            vector_score = _vector_score(normalized_query, metric)
            merged_score = (0.58 * lexical_score) + (0.42 * vector_score)
            rerank_score = _llm_rerank_score(normalized_query, metric, merged_score)
            candidate = SemanticResolveCandidate(
                metric=metric,
                lexical_score=lexical_score,
                vector_score=vector_score,
                merged_score=merged_score,
                rerank_score=rerank_score,
                validation_errors=validation_errors,
                filtered_reason=filtered_reason,
            )
            if candidate.final_score >= _MIN_CANDIDATE_SCORE or filtered_reason or validation_errors:
                scored.append(candidate)

        candidates = sorted(scored, key=lambda item: item.final_score, reverse=True)[:top_k]
        viable = [candidate for candidate in candidates if candidate.final_score >= _MIN_CANDIDATE_SCORE]
        if not viable:
            return SemanticResolveDecision(
                status="no_match",
                semantic_context=[],
                selected=None,
                candidates=candidates,
                normalized_query=normalized_query,
                confidence=0.0,
                reasons=["no_candidate_above_threshold"],
            )

        planner_output = SemanticPlanner().plan(
            query=query,
            normalized_query=normalized_query,
            candidates=viable[:top_k],
        )
        top = _candidate_by_term(viable, planner_output.selected_term) or viable[0]
        confidence = (
            min(top.final_score, planner_output.confidence)
            if planner_output.selected_term
            else top.final_score
        )
        if planner_output.needs_clarification:
            return SemanticResolveDecision(
                status="ambiguous",
                semantic_context=[],
                selected=top,
                candidates=candidates,
                normalized_query=normalized_query,
                confidence=confidence,
                reasons=["planner_requested_clarification"],
                planner_output=planner_output,
            )
        if confidence < _AUTO_SELECT_THRESHOLD:
            return SemanticResolveDecision(
                status="low_confidence",
                semantic_context=[],
                selected=top,
                candidates=candidates,
                normalized_query=normalized_query,
                confidence=confidence,
                reasons=["confidence_below_gate"],
                planner_output=planner_output,
            )
        if len(viable) > 1 and (top.final_score - viable[1].final_score) < _AMBIGUITY_DELTA:
            return SemanticResolveDecision(
                status="ambiguous",
                semantic_context=[],
                selected=top,
                candidates=candidates,
                normalized_query=normalized_query,
                confidence=confidence,
                reasons=["top_candidates_too_close"],
                planner_output=planner_output,
            )
        selected_metric = dict(top.metric)
        selected_metric["_semantic_plan"] = planner_output.to_dict()
        return SemanticResolveDecision(
            status="selected",
            semantic_context=[selected_metric],
            selected=top,
            candidates=candidates,
            normalized_query=normalized_query,
            confidence=confidence,
            reasons=["selected_by_confidence_gate"],
            planner_output=planner_output,
        )


class SemanticPlanner:
    """Structured planner over vector-retrieved semantic candidates.

    If AIAL_SEMANTIC_PLANNER_PROVIDER=openai and OPENAI_API_KEY are configured,
    the planner asks an LLM for strict JSON. Otherwise it uses a deterministic
    local planner with the same output schema.
    """

    def plan(
        self,
        *,
        query: str,
        normalized_query: str,
        candidates: list[SemanticResolveCandidate],
    ) -> SemanticPlannerOutput:
        # Priority 1: full LLM query analyzer (handles synonyms, long queries, clarification)
        from orchestration.semantic.query_analyzer import analyze_query
        full_analysis = analyze_query(query=query, candidates=candidates)
        if full_analysis is not None:
            return full_analysis
        # Priority 2: legacy OpenAI planner (semantic term selection only)
        llm_output = self._plan_with_llm(query=query, candidates=candidates)
        if llm_output is not None:
            return llm_output
        # Priority 3: deterministic regex + scoring fallback
        return _deterministic_plan(query=query, normalized_query=normalized_query, candidates=candidates)

    def _plan_with_llm(
        self,
        *,
        query: str,
        candidates: list[SemanticResolveCandidate],
    ) -> SemanticPlannerOutput | None:
        if os.getenv("AIAL_SEMANTIC_PLANNER_PROVIDER", "").strip().lower() != "openai":
            return None
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        payload = {
            "model": os.getenv("AIAL_SEMANTIC_PLANNER_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            "instructions": (
                "You map Vietnamese analytics questions to governed semantic registry candidates. "
                "Return only JSON with keys: status, selected_term, intent, time_filter, dimensions, "
                "confidence, needs_clarification, clarification_question, rationale. "
                "Do not choose a metric outside candidates. Ask clarification when candidates are ambiguous."
            ),
            "input": {
                "query": query,
                "candidates": [
                    {
                        "term": candidate.metric.get("term"),
                        "aliases": candidate.metric.get("aliases", []),
                        "definition": candidate.metric.get("definition"),
                        "dimensions": candidate.metric.get("dimensions", []),
                        "score": round(candidate.final_score, 4),
                        "examples": candidate.metric.get("examples", []),
                    }
                    for candidate in candidates
                ],
            },
            "temperature": 0,
            "max_output_tokens": 500,
        }
        try:
            response = httpx.post(
                f"{os.getenv('OPENAI_API_BASE_URL', 'https://api.openai.com/v1').rstrip('/')}/responses",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=8.0,
            )
            response.raise_for_status()
            body = response.json()
            text = body.get("output_text") or ""
            return _planner_output_from_payload(_extract_json_object(text))
        except Exception:
            return None


def normalize_semantic_text(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value).casefold())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    without_marks = without_marks.replace("đ", "d")
    return " ".join(without_marks.replace("đ", "d").replace("Ä‘", "d").split())


def _metric_text(metric: dict[str, Any]) -> str:
    retrieval_text = metric.get("retrieval_text")
    if retrieval_text:
        return str(retrieval_text)
    parts = [
        metric.get("term", ""),
        " ".join(str(alias) for alias in metric.get("aliases", []) if alias),
        metric.get("definition", ""),
        metric.get("formula", ""),
        metric.get("owner", ""),
        metric.get("freshness_rule", ""),
        " ".join(str(dim) for dim in metric.get("dimensions", []) if dim),
        " ".join(str(example) for example in metric.get("examples", []) if example),
        " ".join(str(example) for example in metric.get("negative_examples", []) if example),
    ]
    return " ".join(str(part) for part in parts if part)


def _candidate_by_term(
    candidates: list[SemanticResolveCandidate],
    selected_term: str | None,
) -> SemanticResolveCandidate | None:
    if not selected_term:
        return None
    normalized_selected = normalize_semantic_text(selected_term)
    for candidate in candidates:
        if normalize_semantic_text(candidate.metric.get("term", "")) == normalized_selected:
            return candidate
    return None


def _deterministic_plan(
    *,
    query: str,
    normalized_query: str,
    candidates: list[SemanticResolveCandidate],
) -> SemanticPlannerOutput:
    top = candidates[0]
    dimensions = _extract_dimensions(normalized_query)
    entity_filters = _extract_entity_filters(normalized_query)
    parsed_time = parse_time_expression(query)
    time_filter = parsed_time.to_dict()
    intent = "definition" if _is_plain_metric_definition_query(normalized_query) else "metric_value"
    if dimensions:
        intent = "metric_breakdown"
    close_candidates = [
        candidate
        for candidate in candidates[1:3]
        if top.final_score - candidate.final_score < _AMBIGUITY_DELTA
        and not _query_disambiguates_candidate(normalized_query, candidate)
    ]
    if close_candidates:
        terms = [
            str(top.metric.get("term", "")),
            *[str(candidate.metric.get("term", "")) for candidate in close_candidates],
        ]
        return SemanticPlannerOutput(
            status="ambiguous",
            selected_term=str(top.metric.get("term", "")),
            intent=intent,
            time_filter=time_filter,
            dimensions=dimensions,
            entity_filters=entity_filters,
            confidence=top.final_score,
            needs_clarification=True,
            clarification_question=f"Bạn muốn dùng semantic nào: {', '.join(terms)}?",
            rationale="top_candidates_too_close",
        )
    confidence = min(1.0, top.final_score + _planner_context_boost(normalized_query, top.metric))
    return SemanticPlannerOutput(
        status="selected",
        selected_term=str(top.metric.get("term", "")),
        intent=intent,
        time_filter=time_filter,
        dimensions=dimensions,
        entity_filters=entity_filters,
        confidence=confidence,
        needs_clarification=False,
        clarification_question=None,
        rationale="deterministic_structured_planner",
    )


def _extract_dimensions(normalized_query: str) -> list[str]:
    dimensions: list[str] = []
    if any(token in normalized_query for token in ("khu vuc", "vung", "mien", "tinh", "thanh pho", "region")):
        dimensions.append("REGION_CODE")
    if any(token in normalized_query for token in ("kenh", "channel", "online", "retail")):
        dimensions.append("CHANNEL_CODE")
    if any(token in normalized_query for token in ("san pham", "product", "sku")):
        dimensions.append("PRODUCT_CODE")
    if any(token in normalized_query for token in ("nganh hang", "danh muc", "category")):
        dimensions.append("CATEGORY_NAME")
    return dimensions


def _extract_entity_filters(normalized_query: str) -> dict[str, str]:
    """Extract specific dimension value filters (WHERE conditions, not GROUP BY)."""
    filters: dict[str, str] = {}
    # Region — checked in priority order (more specific first)
    if any(t in normalized_query for t in ("ho chi minh", "sai gon", " hcm", "\bhcm\b")):
        filters["REGION_CODE"] = "HCM"
    elif re.search(r"\bhcm\b", normalized_query):
        filters["REGION_CODE"] = "HCM"
    elif any(t in normalized_query for t in ("ha noi", " hn ", "thu do")):
        filters["REGION_CODE"] = "HN"
    elif re.search(r"\bhn\b", normalized_query):
        filters["REGION_CODE"] = "HN"
    elif any(t in normalized_query for t in ("da nang", "danang", "mien trung")):
        filters["REGION_CODE"] = "DANANG"
    # Channel
    if any(t in normalized_query for t in ("online", "truc tuyen")):
        filters["CHANNEL_CODE"] = "ONLINE"
    elif any(t in normalized_query for t in ("retail", "ban le")):
        filters["CHANNEL_CODE"] = "RETAIL"
    elif re.search(r"\bb2b\b", normalized_query):
        filters["CHANNEL_CODE"] = "B2B"
    return filters


def _extract_time_filter(normalized_query: str) -> dict[str, Any] | None:
    # "latest_record" must precede "gan day" to avoid misclassification of "gần đây nhất"
    if re.search(r"gan day nhat|moi nhat|gan nhat|du lieu gan nhat|ngay moi nhat", normalized_query):
        return {"kind": "latest_record"}
    if any(token in normalized_query for token in ("hom nay", "ngay hom nay", "today")):
        return {"kind": "today"}
    if any(token in normalized_query for token in ("hom qua", "ngay hom qua", "yesterday")):
        return {"kind": "yesterday"}
    if any(token in normalized_query for token in ("tuan nay", "this week")):
        return {"kind": "current_week"}
    if any(token in normalized_query for token in ("tuan truoc", "last week")):
        return {"kind": "previous_week"}
    recent_match = re.search(r"\b(\d{1,3})\s*ngay\s*(gan day|qua|vua qua|truoc)\b", normalized_query)
    if recent_match:
        return {"kind": "recent_days", "days": int(recent_match.group(1))}
    if any(token in normalized_query for token in ("may ngay nay", "gan day", "vua qua")):
        return {"kind": "recent_days", "days": 7}
    if "thang nay" in normalized_query:
        return {"kind": "current_month"}
    if "nam nay" in normalized_query:
        return {"kind": "current_year"}
    year_match = re.search(r"\b(20\d{2})\b", normalized_query)
    if year_match:
        quarter_match = re.search(r"\bq([1-4])\b|qu[yý]\s*([1-4])", normalized_query)
        if quarter_match:
            return {
                "kind": "quarter",
                "year": int(year_match.group(1)),
                "quarter": int(quarter_match.group(1) or quarter_match.group(2)),
            }
        return {"kind": "year", "year": int(year_match.group(1))}
    return None


def _is_plain_metric_definition_query(normalized_query: str) -> bool:
    value_words = ("bao nhieu", "the nao", "xu huong", "theo", "gan day", "thang", "nam", "quy", "tong", "tat ca")
    return not any(word in normalized_query for word in value_words)


def _planner_context_boost(normalized_query: str, metric: dict[str, Any]) -> float:
    examples = [normalize_semantic_text(example) for example in metric.get("examples", [])]
    if any(example and SequenceMatcher(None, normalized_query, example).ratio() > 0.55 for example in examples):
        return 0.08
    return 0.0


def _query_disambiguates_candidate(normalized_query: str, candidate: SemanticResolveCandidate) -> bool:
    candidate_term = normalize_semantic_text(candidate.metric.get("term", ""))
    if "ngan sach" in candidate_term and "ngan sach" not in normalized_query:
        return True
    if "ke hoach" in candidate_term and "ke hoach" not in normalized_query:
        return True
    return False


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    import json

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _planner_output_from_payload(payload: dict[str, Any] | None) -> SemanticPlannerOutput | None:
    if payload is None:
        return None
    try:
        return SemanticPlannerOutput(
            status=str(payload.get("status") or "selected"),
            selected_term=str(payload["selected_term"]) if payload.get("selected_term") else None,
            intent=str(payload.get("intent") or "metric_value"),
            time_filter=dict(payload["time_filter"]) if isinstance(payload.get("time_filter"), dict) else None,
            dimensions=[str(item) for item in payload.get("dimensions", []) if str(item).strip()],
            confidence=float(payload.get("confidence", 0.0)),
            needs_clarification=bool(payload.get("needs_clarification", False)),
            clarification_question=(
                str(payload["clarification_question"]) if payload.get("clarification_question") else None
            ),
            rationale=str(payload.get("rationale") or "llm_structured_planner"),
        )
    except (TypeError, ValueError):
        return None


def _lexical_score(normalized_query: str, metric: dict[str, Any]) -> float:
    query_tokens = set(normalized_query.split())
    term_variants = [
        normalize_semantic_text(metric.get("term", "")),
        *[normalize_semantic_text(alias) for alias in metric.get("aliases", [])],
    ]
    exact_scores = []
    for variant in term_variants:
        if not variant:
            continue
        variant_tokens = set(variant.split())
        contains = 1.0 if variant in normalized_query else 0.0
        token_overlap = len(query_tokens & variant_tokens) / max(len(variant_tokens), 1)
        fuzzy = SequenceMatcher(None, normalized_query, variant).ratio()
        exact_scores.append(max(contains, token_overlap * 0.9, fuzzy * 0.65))
    text_tokens = set(normalize_semantic_text(_metric_text(metric)).split())
    retrieval_overlap = len(query_tokens & text_tokens) / max(min(len(query_tokens), 8), 1)
    return min(1.0, max(exact_scores or [0.0]) + min(retrieval_overlap, 1.0) * 0.18)


def _vector_score(normalized_query: str, metric: dict[str, Any]) -> float:
    metric_text = normalize_semantic_text(_metric_text(metric))
    query_vector = _hash_embed(normalized_query, dims=DIMS)
    metric_vector = _hash_embed(metric_text, dims=DIMS)
    return max(0.0, _cosine(query_vector, metric_vector))


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _llm_rerank_score(normalized_query: str, metric: dict[str, Any], merged_score: float) -> float:
    """Deterministic rerank shim for tests and offline deployments.

    Production can swap this function for a structured LLM judge without
    changing audit fields or downstream confidence gates.
    """
    term = normalize_semantic_text(metric.get("term", ""))
    aliases = [normalize_semantic_text(alias) for alias in metric.get("aliases", [])]
    business_synonyms = {
        "ban hang": {"doanh thu", "doanh thu thuan", "net revenue", "sales"},
        "kinh doanh": {"doanh thu", "doanh thu thuan", "loi nhuan"},
        "thu nhap": {"doanh thu", "doanh thu thuan", "net revenue"},
        "revenue": {"doanh thu", "doanh thu thuan", "net revenue"},
    }
    boost = 0.0
    if term and term in normalized_query:
        boost += 0.12
    if any(alias and alias in normalized_query for alias in aliases):
        boost += 0.16
    searchable = {term, *aliases}
    asks_total_revenue = "tat ca doanh thu" in normalized_query or "tong doanh thu" in normalized_query
    if asks_total_revenue and "doanh thu thuan" in searchable:
        boost += 0.16
    if asks_total_revenue and "ngan sach" not in normalized_query and "ke hoach" not in normalized_query:
        if "ngan sach" in term or "budget" in searchable or "ke hoach" in term:
            boost -= 0.12
    for synonym, targets in business_synonyms.items():
        if synonym in normalized_query and searchable.intersection(targets):
            boost += 0.1
    return max(0.0, min(1.0, merged_score + boost))


def _validate_metric(metric: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(metric.get("term", "")).strip():
        errors.append("missing_term")
    if not str(metric.get("definition", "")).strip():
        errors.append("missing_definition")
    if not str(metric.get("formula", "")).strip():
        errors.append("missing_formula")
    return errors


def _security_filter_reason(
    metric: dict[str, Any],
    *,
    principal: JWTClaims | None,
    allowed_terms: set[str] | None,
) -> str | None:
    term = str(metric.get("term", "")).casefold()
    if allowed_terms and term not in allowed_terms:
        return "metric_not_in_role_allowlist"
    security = metric.get("security")
    if not isinstance(security, dict) or principal is None:
        return None
    allowed_roles = {str(role).strip() for role in security.get("allowed_roles", []) if str(role).strip()}
    if allowed_roles and not allowed_roles.intersection(set(principal.roles)):
        return "role_not_allowed"
    sensitivity = security.get("sensitivity_tier")
    if sensitivity is not None and int(sensitivity) > principal.clearance:
        return "clearance_too_low"
    return None
