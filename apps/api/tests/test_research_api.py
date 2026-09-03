import uuid

from app.core.config import settings
from app.modules.research.enums import ResearchProviderName, ResearchStatus
from app.modules.research.models import ResearchRun


def create_account(client, name="Northstar Retail"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://northstar.example",
            "industry": "Retail",
            "region": "Asia Pacific",
            "notes": "Explore demand forecasting and store operations.",
        },
    )
    assert response.status_code == 201
    return response.json()


def start_mock_research(client, account_id):
    response = client.post(
        f"/api/v1/accounts/{account_id}/research-runs",
        json={"provider": "mock"},
    )
    assert response.status_code == 202
    return response.json()


def test_mock_research_is_traceable_and_requires_review(client):
    account = create_account(client)
    run = start_mock_research(client, account["id"])

    assert run["status"] == "needs_review"
    workspace = client.get(f"/api/v1/accounts/{account['id']}/research")
    assert workspace.status_code == 200
    payload = workspace.json()

    assert payload["profile"]["is_simulated"] is True
    assert payload["sources"][0]["source_type"] == "account_input"
    assert payload["profile"]["claims"]
    assert all(claim["citations"] for claim in payload["profile"]["claims"])
    assert all(
        citation["verification_status"] == "direct_input"
        for claim in payload["profile"]["claims"]
        for citation in claim["citations"]
    )

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][0]["status"] == "in_progress"


def test_approval_completes_research_stage_and_records_activity(client):
    account = create_account(client)
    run = start_mock_research(client, account["id"])

    reviewed = client.post(
        f"/api/v1/research-runs/{run['id']}/review",
        json={"decision": "approve", "notes": "Claims and source links checked."},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "completed"

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][0]["status"] == "completed"
    assert workflow["current_stage"] == "opportunity"

    workspace = client.get(f"/api/v1/accounts/{account['id']}/research").json()
    assert all(
        claim["review_status"] == "human_reviewed" for claim in workspace["profile"]["claims"]
    )
    activities = client.get(f"/api/v1/accounts/{account['id']}/activities").json()["items"]
    assert any(item["event_type"] == "research.approved" for item in activities)


def test_rejection_can_be_retried(client):
    account = create_account(client)
    run = start_mock_research(client, account["id"])

    rejected = client.post(
        f"/api/v1/research-runs/{run['id']}/review",
        json={"decision": "reject", "notes": "Add stronger external sources."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    retried = client.post(f"/api/v1/research-runs/{run['id']}/retry")
    assert retried.status_code == 202
    assert retried.json()["status"] == "needs_review"
    assert retried.json()["retry_of_id"] == run["id"]


def test_active_run_prevents_duplicate(client, db_session):
    account = create_account(client)
    active_run = ResearchRun(
        account_id=uuid.UUID(account["id"]),
        status=ResearchStatus.RUNNING,
        provider=ResearchProviderName.MOCK,
    )
    db_session.add(active_run)
    db_session.commit()

    duplicate = client.post(
        f"/api/v1/accounts/{account['id']}/research-runs",
        json={"provider": "mock"},
    )
    assert duplicate.status_code == 409


def test_openai_provider_requires_configuration(client, monkeypatch):
    account = create_account(client)
    monkeypatch.setattr(settings, "openai_api_key", None)

    response = client.post(
        f"/api/v1/accounts/{account['id']}/research-runs",
        json={"provider": "openai"},
    )
    assert response.status_code == 422
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_archived_account_cannot_start_research(client):
    account = create_account(client)
    archived = client.post(f"/api/v1/accounts/{account['id']}/archive")
    assert archived.status_code == 200

    response = client.post(
        f"/api/v1/accounts/{account['id']}/research-runs",
        json={"provider": "mock"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
