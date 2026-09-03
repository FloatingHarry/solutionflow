def create_account(client, name="Agent Test Account"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://example.com",
            "industry": "Logistics",
            "region": "Europe",
            "notes": "Reduce manual document handling.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_guided_agent_plans_and_executes_approved_research(client):
    account = create_account(client)
    account_id = account["id"]

    workspace = client.get(f"/api/v1/accounts/{account_id}/agent")
    assert workspace.status_code == 200
    assert workspace.json()["mode"] == "guided"
    assert workspace.json()["live_agent_available"] is False

    planned = client.post(
        f"/api/v1/accounts/{account_id}/agent/runs",
        json={"goal": "Prepare the safest next step"},
    )
    assert planned.status_code == 201
    run = planned.json()
    assert run["status"] == "awaiting_approval"
    assert run["provider"] == "guided"
    assert run["action"]["key"] == "run_research"
    assert run["action"]["status"] == "pending"
    assert [item["tool"] for item in run["trace"]] == [
        "inspect_account",
        "inspect_workflow",
        "inspect_stage_artifacts",
    ]

    approved = client.post(
        f"/api/v1/agent-runs/{run['id']}/approve",
        json={"note": "Approved for a simulated test run"},
    )
    assert approved.status_code == 200
    completed = approved.json()
    assert completed["status"] == "action_completed"
    assert completed["action"]["status"] == "executed"
    assert completed["action"]["result"]["provider"] == "mock"

    research = client.get(f"/api/v1/accounts/{account_id}/research").json()
    assert research["latest_run"]["status"] == "needs_review"
    assert research["profile"]["is_simulated"] is True

    next_run = client.post(
        f"/api/v1/accounts/{account_id}/agent/runs",
        json={"goal": "Continue without skipping approval"},
    ).json()
    assert next_run["status"] == "completed"
    assert next_run["action"]["key"] == "open_research_review"
    assert next_run["action"]["requires_approval"] is False

    activities = client.get(f"/api/v1/accounts/{account_id}/activities").json()["items"]
    event_types = {item["event_type"] for item in activities}
    assert "agent.run_created" in event_types
    assert "agent.action_executed" in event_types


def test_agent_action_can_be_rejected_and_cannot_be_replayed(client):
    account = create_account(client, "Reject Agent Action")
    run = client.post(
        f"/api/v1/accounts/{account['id']}/agent/runs",
        json={"goal": "Start research"},
    ).json()

    rejected = client.post(
        f"/api/v1/agent-runs/{run['id']}/reject",
        json={"note": "Need legal review first"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["action"]["status"] == "rejected"

    replay = client.post(f"/api/v1/agent-runs/{run['id']}/approve", json={})
    assert replay.status_code == 409


def test_archived_account_agent_is_read_only(client):
    account = create_account(client, "Archived Agent Account")
    client.post(f"/api/v1/accounts/{account['id']}/archive")

    response = client.post(
        f"/api/v1/accounts/{account['id']}/agent/runs",
        json={"goal": "Continue workflow"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
