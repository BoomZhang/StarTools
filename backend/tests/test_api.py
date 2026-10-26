from fastapi.testclient import TestClient

from app.main import app


def test_root_exposes_service_info() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "随手工具箱"


def test_health_reports_component_checks() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert {"database", "redis", "ocr"} <= set(body["checks"])


def test_site_returns_catalog_and_limits() -> None:
    with TestClient(app) as client:
        response = client.get("/api/site")
    assert response.status_code == 200
    body = response.json()
    assert body["site"]["total_tools"] == 39
    assert len(body["categories"]) == 7
    codes = {tool["code"] for tool in body["tools"]}
    assert len(codes) == 39
    assert {"IMG-01", "TXT-01", "ENC-01", "QR-01", "OCR-01", "AV-07"} <= codes


def test_admin_requires_login() -> None:
    with TestClient(app) as client:
        response = client.get("/api/admin/tools")
    assert response.status_code == 401


def test_admin_login_rejects_wrong_password() -> None:
    with TestClient(app) as client:
        response = client.post("/api/admin/login", json={"username": "admin", "password": "wrong-password"})
    assert response.status_code == 401
    assert "账号或密码错误" in response.json()["detail"]["message"]


def test_feedback_rejects_meaningless_description() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/feedback",
            json={"type": "bug", "description": "aaaaaaaaaaaaaaaa", "context": {"path": "/startools/"}},
        )
    assert response.status_code == 422
