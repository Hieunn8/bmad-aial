"""Tests for observability infrastructure configuration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INFRA = PROJECT_ROOT / "infra"
OBSERVABILITY = INFRA / "observability"


class TestObservabilityFiles:
    def test_observability_directories_exist(self) -> None:
        assert (OBSERVABILITY / "otel-collector").is_dir()
        assert (OBSERVABILITY / "tempo").is_dir()
        assert (OBSERVABILITY / "prometheus").is_dir()
        assert (OBSERVABILITY / "grafana").is_dir()


class TestOtelCollectorConfig:
    @pytest.fixture()
    def config(self) -> dict:
        path = OBSERVABILITY / "otel-collector" / "config.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_otlp_receiver_enabled(self, config: dict) -> None:
        assert "otlp" in config["receivers"]
        assert {"grpc", "http"} <= set(config["receivers"]["otlp"]["protocols"].keys())

    def test_trace_pipeline_exports_to_tempo_and_spanmetrics(self, config: dict) -> None:
        pipeline = config["service"]["pipelines"]["traces"]
        assert "otlp/tempo" in pipeline["exporters"]
        assert "spanmetrics" in pipeline["exporters"]

    def test_metrics_pipeline_exports_prometheus(self, config: dict) -> None:
        pipeline = config["service"]["pipelines"]["metrics"]
        assert pipeline["receivers"] == ["spanmetrics"]
        assert pipeline["exporters"] == ["prometheus"]


class TestTempoConfig:
    @pytest.fixture()
    def config(self) -> dict:
        path = OBSERVABILITY / "tempo" / "config.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_tempo_receives_otlp(self, config: dict) -> None:
        protocols = config["distributor"]["receivers"]["otlp"]["protocols"]
        assert {"grpc", "http"} <= set(protocols.keys())

    def test_tempo_uses_local_trace_storage(self, config: dict) -> None:
        trace_storage = config["storage"]["trace"]
        assert trace_storage["backend"] == "local"
        assert trace_storage["local"]["path"] == "/tmp/tempo/traces"


class TestPrometheusConfig:
    @pytest.fixture()
    def config(self) -> dict:
        path = OBSERVABILITY / "prometheus" / "prometheus.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_prometheus_scrapes_otel_collector(self, config: dict) -> None:
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        assert "otel-collector" in jobs
        assert "otel-collector:9464" in jobs["otel-collector"]["static_configs"][0]["targets"]

    def test_prometheus_scrapes_tempo(self, config: dict) -> None:
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        assert "tempo" in jobs
        assert "tempo:3200" in jobs["tempo"]["static_configs"][0]["targets"]

    def test_prometheus_scrapes_orchestration_metrics(self, config: dict) -> None:
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        assert "orchestration" in jobs
        assert jobs["orchestration"]["metrics_path"] == "/metrics"
        assert "host.docker.internal:8090" in jobs["orchestration"]["static_configs"][0]["targets"]


class TestGrafanaProvisioning:
    @pytest.fixture()
    def datasources(self) -> dict:
        path = OBSERVABILITY / "grafana" / "provisioning" / "datasources" / "datasources.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @pytest.fixture()
    def dashboards(self) -> dict:
        path = OBSERVABILITY / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_grafana_provisions_prometheus_and_tempo(self, datasources: dict) -> None:
        names = {item["name"] for item in datasources["datasources"]}
        assert {"Prometheus", "Tempo"} <= names

    def test_grafana_dashboard_provider_uses_repo_dashboards_path(self, dashboards: dict) -> None:
        provider = dashboards["providers"][0]
        assert provider["type"] == "file"
        assert provider["options"]["path"] == "/var/lib/grafana/dashboards"


class TestGrafanaDashboards:
    def test_aial_overview_dashboard_contains_required_panels(self) -> None:
        path = OBSERVABILITY / "grafana" / "dashboards" / "aial-overview.json"
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        panel_titles = {panel["title"] for panel in dashboard["panels"]}
        assert "P50/P95 Request Latency by Service" in panel_titles
        assert "Error Rate %" in panel_titles
        assert "LangGraph Node Execution Count per Session" in panel_titles
        assert "Semantic Query Cache Hit Rate" in panel_titles
        assert "Semantic Query Cache Volume" in panel_titles

    def test_llm_dashboard_contains_langfuse_panels(self) -> None:
        path = OBSERVABILITY / "grafana" / "dashboards" / "llm-observability.json"
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        panel_titles = {panel["title"] for panel in dashboard["panels"]}
        assert "LLM Token Usage" in panel_titles
        assert "LLM Observation Latency P95" in panel_titles


class TestComposeObservabilityServices:
    @pytest.fixture()
    def compose(self) -> dict:
        path = INFRA / "docker-compose.dev.yml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_core_observability_services_present(self, compose: dict) -> None:
        services = compose["services"]
        assert {"otel-collector", "tempo", "prometheus", "grafana"} <= set(services.keys())

    def test_collector_exposes_otlp_ports(self, compose: dict) -> None:
        ports = compose["services"]["otel-collector"]["ports"]
        assert "4317:4317" in ports
        assert "4318:4318" in ports

    def test_grafana_provisions_dashboard_mounts(self, compose: dict) -> None:
        volumes = compose["services"]["grafana"]["volumes"]
        assert any("grafana/provisioning/datasources" in entry for entry in volumes)
        assert any("grafana/provisioning/dashboards" in entry for entry in volumes)
        assert any("grafana/dashboards" in entry for entry in volumes)

    def test_langfuse_profile_services_present(self, compose: dict) -> None:
        services = compose["services"]
        assert {"langfuse-web", "langfuse-worker", "langfuse-clickhouse", "langfuse-minio"} <= set(services.keys())
        assert services["langfuse-web"]["profiles"] == ["llm-observability"]
        assert services["langfuse-worker"]["profiles"] == ["llm-observability"]
