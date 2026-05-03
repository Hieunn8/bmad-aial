"""Business Glossary API — Story 2A.2."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.glossary import GlossaryRepository
from orchestration.semantic.management import get_semantic_layer_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)

_repo = GlossaryRepository(connection_factory=None)


class GlossaryEntry(BaseModel):
    term: str
    definition: str
    formula: str
    owner: str
    freshness_rule: str


class GlossaryNotFound(BaseModel):
    status: str = "not_found"


@router.get("/v1/glossary/{term}")
async def get_glossary_term(
    term: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> GlossaryEntry | GlossaryNotFound:
    del principal
    managed = get_semantic_layer_service().get_metric(term)
    if managed is not None:
        return GlossaryEntry(
            term=managed.term,
            definition=managed.definition,
            formula=managed.formula,
            owner=managed.owner,
            freshness_rule=managed.freshness_rule,
        )
    result = _repo.find(term)
    if result is None:
        return GlossaryNotFound()
    return GlossaryEntry(**result)
