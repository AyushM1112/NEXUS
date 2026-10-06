from app.app import app

def test_jenkins_api_is_graceful_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.app.JENKINS_URL", "")
    monkeypatch.setattr("app.app.JENKINS_USER", "")
    monkeypatch.setattr("app.app.JENKINS_TOKEN", "")
    response = app.test_client().get("/api/jenkins/overview")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["connected"] is False
    assert payload["configured"] is False
