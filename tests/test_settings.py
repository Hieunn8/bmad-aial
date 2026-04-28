import os
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.settings import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_ENV = {
    "AIAL_KONG_ADMIN_TOKEN": "dev-kong-token",
    "AIAL_KEYCLOAK_CLIENT_SECRET": "dev-keycloak-secret",
    "AIAL_ORACLE_USERNAME": "dev_oracle_user",
    "AIAL_ORACLE_PASSWORD": "dev_oracle_pass",
    "AIAL_ORACLE_DSN": "localhost:1521/FREEPDB1",
}


def test_settings_load_success(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in REQUIRED_ENV.items():
        monkeypatch.setenv(k, v)

    settings = Settings()

    assert settings.kong_admin_token == REQUIRED_ENV["AIAL_KONG_ADMIN_TOKEN"]
    assert settings.keycloak_client_secret == REQUIRED_ENV["AIAL_KEYCLOAK_CLIENT_SECRET"]
    assert settings.oracle_username == REQUIRED_ENV["AIAL_ORACLE_USERNAME"]


def test_settings_fail_fast_when_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in REQUIRED_ENV:
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setenv("AIAL_KONG_ADMIN_TOKEN", "dev-kong-token")

    with pytest.raises(ValidationError):
        Settings()


def test_runtime_entrypoint_fails_fast_when_secret_missing() -> None:
    env = os.environ.copy()
    for key in REQUIRED_ENV:
        env.pop(key, None)

    env["AIAL_KONG_ADMIN_TOKEN"] = "dev-kong-token"
    env["PYTHONPATH"] = str(PROJECT_ROOT / "services")

    result = subprocess.run(
        ["python", "-m", "app.main"],
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "ValidationError" in (result.stderr + result.stdout)
    assert "AIAL_KEYCLOAK_CLIENT_SECRET" in (result.stderr + result.stdout)
