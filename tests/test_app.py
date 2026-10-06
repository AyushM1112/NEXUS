from app.app import app


def test_home_page():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"AI DEVOPS OPTIMIZER BROKEN" in response.data
    assert b"16014123017" in response.data


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "healthy"


def test_pipeline_source_endpoint():
    client = app.test_client()
    response = client.get("/api/pipeline-source")
    assert response.status_code == 200
    assert "pipeline" in response.get_json()["source"].lower()


def test_benchmarks_endpoint():
    client = app.test_client()
    response = client.get("/api/benchmarks")
    assert response.status_code == 200
    assert "benchmarks" in response.get_json()
