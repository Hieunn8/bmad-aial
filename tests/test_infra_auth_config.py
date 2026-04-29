"""Tests for infrastructure auth configuration files.

Validates that Keycloak realm, Kong config, and Cerbos policies
are structurally correct and satisfy Story 1.3 acceptance criteria.
"""

import json
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INFRA = PROJECT_ROOT / "infra"


class TestKeycloakRealmExport:
    @pytest.fixture()
    def realm(self) -> dict:
        path = INFRA / "keycloak" / "realm-export.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_realm_name_is_aial(self, realm: dict) -> None:
        assert realm["realm"] == "aial"

    def test_realm_is_enabled(self, realm: dict) -> None:
        assert realm["enabled"] is True

    def test_access_token_lifespan_is_8h(self, realm: dict) -> None:
        assert realm["accessTokenLifespan"] == 28800

    def test_refresh_token_rotation_enabled(self, realm: dict) -> None:
        assert realm["revokeRefreshToken"] is True

    def test_client_aial_web_exists(self, realm: dict) -> None:
        clients = {c["clientId"]: c for c in realm["clients"]}
        assert "aial-web" in clients
        assert clients["aial-web"]["publicClient"] is True

    def test_client_aial_api_exists(self, realm: dict) -> None:
        clients = {c["clientId"]: c for c in realm["clients"]}
        assert "aial-api" in clients
        assert clients["aial-api"]["publicClient"] is False

    def test_aial_claims_scope_has_department_mapper(self, realm: dict) -> None:
        scope = next(s for s in realm["clientScopes"] if s["name"] == "aial-claims")
        mapper_names = [m["name"] for m in scope["protocolMappers"]]
        assert "department-mapper" in mapper_names

    def test_aial_claims_scope_has_clearance_mapper(self, realm: dict) -> None:
        scope = next(s for s in realm["clientScopes"] if s["name"] == "aial-claims")
        mapper_names = [m["name"] for m in scope["protocolMappers"]]
        assert "clearance-mapper" in mapper_names

    def test_aial_claims_scope_has_roles_mapper(self, realm: dict) -> None:
        scope = next(s for s in realm["clientScopes"] if s["name"] == "aial-claims")
        mapper_names = [m["name"] for m in scope["protocolMappers"]]
        assert "realm-roles-mapper" in mapper_names

    def test_department_mapper_in_access_token(self, realm: dict) -> None:
        scope = next(s for s in realm["clientScopes"] if s["name"] == "aial-claims")
        mapper = next(m for m in scope["protocolMappers"] if m["name"] == "department-mapper")
        assert mapper["config"]["access.token.claim"] == "true"
        assert mapper["config"]["claim.name"] == "department"

    def test_clearance_mapper_in_access_token(self, realm: dict) -> None:
        scope = next(s for s in realm["clientScopes"] if s["name"] == "aial-claims")
        mapper = next(m for m in scope["protocolMappers"] if m["name"] == "clearance-mapper")
        assert mapper["config"]["access.token.claim"] == "true"
        assert mapper["config"]["claim.name"] == "clearance"

    def test_roles_defined(self, realm: dict) -> None:
        role_names = {r["name"] for r in realm["roles"]["realm"]}
        assert {"admin", "user", "viewer"} <= role_names

    def test_dev_users_have_required_attributes(self, realm: dict) -> None:
        for user in realm["users"]:
            assert "department" in user["attributes"], f"{user['username']} missing department"
            assert "clearance" in user["attributes"], f"{user['username']} missing clearance"

    def test_ldap_federation_configured(self, realm: dict) -> None:
        providers = realm.get("components", {}).get("org.keycloak.storage.UserStorageProvider", [])
        assert len(providers) >= 1, "No LDAP user federation provider configured"
        ldap = providers[0]
        assert ldap["providerId"] == "ldap"
        assert ldap["config"]["connectionUrl"] == ["ldap://aial-openldap:389"]

    def test_ldap_federation_has_attribute_mappers(self, realm: dict) -> None:
        providers = realm["components"]["org.keycloak.storage.UserStorageProvider"]
        ldap = providers[0]
        mappers = ldap["subComponents"]["org.keycloak.storage.ldap.mappers.LDAPStorageMapper"]
        mapper_names = {m["name"] for m in mappers}
        assert "username" in mapper_names
        assert "email" in mapper_names
        assert "department" in mapper_names
        assert "clearance" in mapper_names
        assert "realm-role-mapper" in mapper_names


class TestKongConfig:
    @pytest.fixture()
    def config(self) -> dict:
        path = INFRA / "kong" / "kong.yml.tmpl"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_format_version(self, config: dict) -> None:
        assert config["_format_version"] == "3.0"

    def test_chat_query_route_exists(self, config: dict) -> None:
        routes = []
        for svc in config.get("services", []):
            routes.extend(svc.get("routes", []))
        route_names = [r["name"] for r in routes]
        assert "chat-query" in route_names

    def test_chat_query_route_path(self, config: dict) -> None:
        routes = []
        for svc in config.get("services", []):
            routes.extend(svc.get("routes", []))
        chat_route = next(r for r in routes if r["name"] == "chat-query")
        assert "/v1/chat/query" in chat_route["paths"]

    def test_jwt_plugin_configured(self, config: dict) -> None:
        plugin_names = [p["name"] for p in config.get("plugins", [])]
        assert "jwt" in plugin_names

    def test_post_function_plugin_configured(self, config: dict) -> None:
        plugin_names = [p["name"] for p in config.get("plugins", [])]
        assert "post-function" in plugin_names

    def test_rate_limiting_plugin_configured(self, config: dict) -> None:
        plugin_names = [p["name"] for p in config.get("plugins", [])]
        assert "rate-limiting" in plugin_names

    def test_rate_limiting_day_limit_100(self, config: dict) -> None:
        rl = next(p for p in config["plugins"] if p["name"] == "rate-limiting")
        assert rl["config"]["day"] == 100

    def test_jwt_uses_rs256_with_public_key_slot(self, config: dict) -> None:
        consumers = config.get("consumers", [])
        assert len(consumers) > 0
        jwt_secrets = consumers[0].get("jwt_secrets", [])
        rs256_secrets = [s for s in jwt_secrets if s["algorithm"] == "RS256"]
        assert len(rs256_secrets) >= 1
        assert "rsa_public_key" in rs256_secrets[0], "RS256 jwt_secret must include rsa_public_key"

    def test_upstream_not_kong_proxy_port(self, config: dict) -> None:
        for svc in config.get("services", []):
            url = svc.get("url", "")
            assert ":8000" not in url, f"Service {svc['name']} upstream {url} points to Kong's own proxy port 8000"


class TestCerbosPolicies:
    def test_policies_directory_exists(self) -> None:
        assert (INFRA / "cerbos" / "policies").is_dir()

    def test_at_least_one_policy_file(self) -> None:
        policies = list((INFRA / "cerbos" / "policies").glob("*.yaml"))
        assert len(policies) >= 1

    def test_api_chat_policy_exists(self) -> None:
        policy_path = INFRA / "cerbos" / "policies" / "resource_api.yaml"
        assert policy_path.exists()
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        assert policy["apiVersion"] == "api.cerbos.dev/v1"
        assert policy["resourcePolicy"]["resource"] == "api:chat"

    def test_api_chat_policy_allows_user_with_query(self) -> None:
        policy_path = INFRA / "cerbos" / "policies" / "resource_api.yaml"
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        rules = policy["resourcePolicy"]["rules"]
        allow_rules = [r for r in rules if r["effect"] == "EFFECT_ALLOW" and "query" in r["actions"]]
        assert len(allow_rules) >= 1
        allowed_roles = set()
        for r in allow_rules:
            allowed_roles.update(r["roles"])
        assert "user" in allowed_roles
        assert "admin" in allowed_roles

    def test_api_chat_policy_denies_viewer(self) -> None:
        policy_path = INFRA / "cerbos" / "policies" / "resource_api.yaml"
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        rules = policy["resourcePolicy"]["rules"]
        deny_rules = [r for r in rules if r["effect"] == "EFFECT_DENY" and "viewer" in r["roles"]]
        assert len(deny_rules) >= 1

    def test_cerbos_conf_yaml_valid(self) -> None:
        conf_path = INFRA / "cerbos" / "conf.yaml"
        conf = yaml.safe_load(conf_path.read_text(encoding="utf-8"))
        assert conf["server"]["httpListenAddr"] == ":3592"
        assert conf["storage"]["driver"] == "disk"
