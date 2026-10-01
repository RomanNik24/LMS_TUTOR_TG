"""Регрессионные проверки docker-compose.yml и Dockerfile.

История: в ходе параллельных веток дважды терялись важные настройки:
  - DB_PORT: 5432 для контейнеров внутри docker-сети (postgres слушает 5432,
    хостовый маппинг 15432 к ним не относится);
  - volume lms_uploads для data/uploads сервиса api (без него загрузки
    учеников терялись при пересоздании контейнера).
Эти тесты не дают таким регрессиям снова уйти незамеченными.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
DOCKERFILE = ROOT / "Dockerfile"

# Сервисы, которые ходят в Postgres изнутри docker-сети
DB_SERVICES = ("migrate", "api", "bot", "worker")


@pytest.fixture(scope="module")
def compose() -> dict:
    assert COMPOSE_FILE.exists(), "docker-compose.yml отсутствует в репозитории"
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))


class TestComposeDbNetwork:
    def test_db_port_inside_network(self, compose):
        """Каждый БД-сервис обязан явным образом использовать DB_PORT=5432."""
        for name in DB_SERVICES:
            env = compose["services"][name].get("environment", {})
            assert str(env.get("DB_PORT")) == "5432", (
                f"Сервис {name}: потерян DB_PORT=5432 (внутри сети postgres "
                "доступен на 5432; хостовый маппинг его не касается)"
            )

    def test_db_host(self, compose):
        for name in DB_SERVICES:
            env = compose["services"][name].get("environment", {})
            assert env.get("DB_HOST") == "postgres"

    def test_postgres_host_mapping_kept(self, compose):
        """Хостовый проброс порта postgres не должен молча измениться."""
        ports = compose["services"]["postgres"].get("ports", [])
        assert any(":5432" in p for p in ports), ports


class TestUploadsPersistence:
    def test_api_has_uploads_volume(self, compose):
        mounts = compose["services"]["api"].get("volumes", [])
        assert any(
            m.endswith(":/app/data/uploads") and m.split(":")[0] == "lms_uploads"
            for m in mounts
        ), f"У сервиса api потерян volume lms_uploads -> /app/data/uploads: {mounts}"

    def test_uploads_volume_declared(self, compose):
        assert "lms_uploads" in (compose.get("volumes") or {}), \
            "top-level volumes: потерян lms_uploads"

    def test_dockerfile_documents_uploads_volume(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        assert "/app/data/uploads" in text, \
            "В Dockerfile потеряна декларация VOLUME для каталога загрузок"


class TestComposeStructure:
    def test_all_services_present(self, compose):
        expected = {"postgres", "redis", "migrate", "api", "bot", "webapp", "worker"}
        assert expected <= set(compose["services"]), \
            f"Пропали сервисы: {expected - set(compose['services'])}"

    def test_worker_entrypoint(self, compose):
        assert compose["services"]["worker"]["command"] == ["python", "-m", "src.worker"]

    def test_webapp_upstream_url_points_to_service(self, compose):
        env = compose["services"]["api"]["environment"]
        assert env["WEBAPP_UPSTREAM_URL"] == "http://webapp:8550"
