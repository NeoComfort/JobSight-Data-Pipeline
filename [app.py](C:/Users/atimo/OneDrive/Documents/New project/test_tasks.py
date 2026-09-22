import pytest

from app import app, task_ids, tasks


@pytest.fixture(autouse=True)
def reset_tasks():
    tasks.clear()
    # IDs do not affect the API behaviour being tested; each test reads IDs from responses.
    yield
    tasks.clear()


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def create_task(client, **overrides):
    payload = {"title": "Write tests", "description": "Test TaskFlow", "status": "todo"}
    payload.update(overrides)
    return client.post("/tasks", json=payload)


def test_health_check_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"TaskFlow" in response.data


def test_create_task_returns_created_task(client):
    response = create_task(client)
    body = response.get_json()
    assert response.status_code == 201
    assert body["title"] == "Write tests"
    assert body["status"] == "todo"
    assert isinstance(body["id"], int)


def test_create_task_requires_a_non_empty_title(client):
    response = client.post("/tasks", json={"title": "   "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "title must be a non-empty string."


def test_create_task_rejects_invalid_status(client):
    response = create_task(client, status="waiting")
    assert response.status_code == 400
    assert "status must be" in response.get_json()["error"]


def test_list_tasks_can_filter_by_status(client):
    create_task(client, title="First", status="todo")
    create_task(client, title="Second", status="done")
    response = client.get("/tasks?status=done")
    assert response.status_code == 200
    assert [task["title"] for task in response.get_json()] == ["Second"]


def test_get_task_returns_not_found_for_unknown_id(client):
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "task not found."


def test_update_task_changes_requested_fields(client):
    task_id = create_task(client).get_json()["id"]
    response = client.patch(f"/tasks/{task_id}", json={"status": "done", "title": "Finished tests"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "done"
    assert response.get_json()["title"] == "Finished tests"


def test_delete_task_removes_task(client):
    task_id = create_task(client).get_json()["id"]
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404
