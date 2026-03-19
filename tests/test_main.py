"""HabitFlow 기본 동작 테스트"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with (
        patch("app.database.init_db", new_callable=AsyncMock),
        patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.start"),
        patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.shutdown"),
        patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.add_job"),
    ):
        from app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_root(client):
    """루트 엔드포인트가 200을 반환하고 service 필드를 포함해야 한다"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "HabitFlow API"
    assert data["status"] == "healthy"


def test_health(client):
    """헬스체크 엔드포인트가 200을 반환해야 한다"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_docs_available(client):
    """/docs 엔드포인트가 접근 가능해야 한다"""
    response = client.get("/docs")
    assert response.status_code == 200
