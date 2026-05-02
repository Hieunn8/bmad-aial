"""Policy Enforcement Service — Story 3.2.

Cerbos drives the pre-retrieval authorization decision.
The service calls Cerbos first; JWT claims inform Cerbos but do NOT
independently substitute for Cerbos output.

Walking-skeleton constraint: Cerbos' CheckResources API returns a boolean
per resource+action. Full PlanResources / attribute output (multi-dept grants,
classification ceiling override) is wired in Epic 4. Until then, `allowed_departments`
and `max_classification` default to the JWT values IFF Cerbos grants the base action.
This is the extensibility seam — Epic 4 replaces lines marked [Epic4-hook].
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aial_shared.auth.keycloak import JWTClaims

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    allowed: bool
    allowed_departments: list[str] = field(default_factory=list)
    max_classification: int = 0
    denial_reason: str | None = None


class PolicyEnforcementService:
    def __init__(self, cerbos_client: object, *, timeout_ms: int = 500) -> None:
        self._cerbos = cerbos_client
        self._timeout_ms = timeout_ms

    def enforce(self, principal: JWTClaims) -> PolicyDecision:
        # --- Cerbos gate (always runs first) ---
        try:
            cerbos_allowed = self._cerbos.is_allowed(
                principal, "api:chat", "default", "query",
                resource_attr={"domain": principal.department},
            )
        except TimeoutError:
            logger.warning("Cerbos timeout for principal %s — fail-closed", principal.sub)
            return PolicyDecision(allowed=False, denial_reason="cerbos_timeout")
        except Exception as exc:
            if "timeout" in str(exc).lower():
                return PolicyDecision(allowed=False, denial_reason="cerbos_timeout")
            logger.warning("Cerbos error for principal %s: %s — fail-closed", principal.sub, exc)
            return PolicyDecision(allowed=False, denial_reason="cerbos_error")

        if not cerbos_allowed:
            return PolicyDecision(allowed=False, denial_reason="cerbos_deny")

        # --- [Epic4-hook] Replace below with PlanResources output when available ---
        # For now, Cerbos ALLOW means we honour the JWT department + clearance.
        # Epic 4 will call cerbos.plan_resources() to get allowed_departments list
        # and classification ceiling from the policy, replacing these defaults.
        allowed_departments: list[str] = [principal.department]
        max_classification: int = principal.clearance

        return PolicyDecision(
            allowed=True,
            allowed_departments=allowed_departments,
            max_classification=max_classification,
        )
