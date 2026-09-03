from app.modules.accounts.enums import STAGE_ORDER


def create_account(client, name="Example Retail UK"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://example.com",
            "industry": "Retail",
            "region": "UK",
            "notes": "Priority account",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_account_initializes_workflow_and_activity(client):
    account = create_account(client)

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow")
    assert workflow.status_code == 200
    payload = workflow.json()
    assert payload["current_stage"] == "research"
    assert [stage["stage"] for stage in payload["stages"]] == [stage.value for stage in STAGE_ORDER]
    assert all(stage["status"] == "not_started" for stage in payload["stages"])

    activity = client.get(f"/api/v1/accounts/{account['id']}/activities")
    assert activity.status_code == 200
    assert activity.json()["total"] == 1
    assert activity.json()["items"][0]["event_type"] == "account.created"


def test_update_search_archive_and_restore(client):
    account = create_account(client)
    account_id = account["id"]

    updated = client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"industry": "Consumer retail", "region": "Europe"},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    search = client.get("/api/v1/accounts", params={"q": "consumer"})
    assert search.status_code == 200
    assert search.json()["total"] == 1

    archived = client.post(f"/api/v1/accounts/{account_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/api/v1/accounts").json()["total"] == 0
    assert client.get("/api/v1/accounts", params={"include_archived": True}).json()["total"] == 1

    restored = client.post(f"/api/v1/accounts/{account_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_workflow_enforces_order_and_records_reason(client):
    account = create_account(client)
    account_id = account["id"]

    invalid = client.post(
        f"/api/v1/accounts/{account_id}/workflow/transitions",
        json={"stage": "discovery", "status": "in_progress", "reason": "Jump ahead"},
    )
    assert invalid.status_code == 409

    started = client.post(
        f"/api/v1/accounts/{account_id}/workflow/transitions",
        json={"stage": "research", "status": "in_progress", "reason": "Begin research"},
    )
    assert started.status_code == 200
    assert started.json()["stages"][0]["status"] == "in_progress"

    completed = client.post(
        f"/api/v1/accounts/{account_id}/workflow/transitions",
        json={"stage": "research", "status": "completed", "reason": "Sources reviewed"},
    )
    assert completed.status_code == 200
    assert completed.json()["current_stage"] == "opportunity"

    activities = client.get(f"/api/v1/accounts/{account_id}/activities").json()["items"]
    completion_activity = next(
        item for item in activities if item["metadata"].get("to") == "completed"
    )
    assert completion_activity["metadata"]["reason"] == "Sources reviewed"


def test_blank_account_name_is_rejected(client):
    response = client.post("/api/v1/accounts", json={"name": "   "})
    assert response.status_code == 422


def test_website_is_normalized_and_unsafe_scheme_is_rejected(client):
    created = client.post("/api/v1/accounts", json={"name": "GLM", "website": "example.com"})
    assert created.status_code == 201
    assert created.json()["website"] == "https://example.com"

    unsafe = client.post(
        "/api/v1/accounts", json={"name": "Unsafe", "website": "javascript:alert(1)"}
    )
    assert unsafe.status_code == 422
