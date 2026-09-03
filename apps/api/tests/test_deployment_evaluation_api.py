from test_business_case_api import complete_poc
from test_poc_api import create_account


def approved_business_case(client, account_id):
    complete_poc(client, account_id)
    case = client.post(f"/api/v1/accounts/{account_id}/business-cases/generate").json()
    response = client.post(
        f"/api/v1/business-cases/{case['id']}/review",
        json={"decision": "approve", "notes": "Business case approved for deployment."},
    )
    assert response.status_code == 200
    return response.json()


def test_deployment_requires_approved_business_case(client):
    account = create_account(client, "Deployment Prerequisite")

    response = client.post(f"/api/v1/accounts/{account['id']}/deployment-plans/generate")

    assert response.status_code == 409
    assert "Approve the business case" in response.json()["detail"]


def test_deployment_plan_checklist_blocker_and_completion(client):
    account = create_account(client, "Deployment Flow")
    case = approved_business_case(client, account["id"])

    generated = client.post(
        f"/api/v1/accounts/{account['id']}/deployment-plans/generate"
    )
    assert generated.status_code == 201
    plan = generated.json()
    assert plan["business_case_id"] == case["id"]
    assert plan["environment"] == "eu_cloud"
    assert plan["readiness_score"] == 0
    assert len(plan["checklist_items"]) == 6

    updated = client.patch(
        f"/api/v1/deployment-plans/{plan['id']}",
        json={
            "owner": "Delivery Lead",
            "rollout_strategy": "Pilot with one team, validate exit criteria, then expand.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["owner"] == "Delivery Lead"

    blocked_item = plan["checklist_items"][0]
    blocked = client.patch(
        f"/api/v1/deployment-checklist-items/{blocked_item['id']}",
        json={"status": "blocked", "evidence_notes": "Security review is pending."},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][7]["status"] == "blocked"

    plan = blocked.json()
    for item in plan["checklist_items"]:
        response = client.patch(
            f"/api/v1/deployment-checklist-items/{item['id']}",
            json={
                "owner": "Delivery Team",
                "status": "completed",
                "evidence_notes": "Approval evidence recorded.",
            },
        )
        assert response.status_code == 200
        plan = response.json()
    assert plan["readiness_score"] == 100
    assert plan["status"] == "in_progress"

    completed = client.post(
        f"/api/v1/deployment-plans/{plan['id']}/complete",
        json={"notes": "All production-readiness owners approved launch."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    workspace = client.get(f"/api/v1/accounts/{account['id']}/deployment").json()
    assert workspace["deployment_stage_status"] == "completed"
    assert workspace["current_stage"] == "deployment"

    locked = client.patch(
        f"/api/v1/deployment-plans/{plan['id']}", json={"owner": "Another owner"}
    )
    assert locked.status_code == 409
    assert "read-only" in locked.json()["detail"]


def test_demo_portfolio_and_system_evaluation_are_idempotent(client):
    seeded = client.post("/api/v1/demo-accounts/seed")
    assert seeded.status_code == 201
    workspace = seeded.json()
    assert len(workspace["demo_accounts"]) == 5
    assert all(item["workflow_completion"] == 100 for item in workspace["demo_accounts"])
    assert all(
        item["deployment_plan_status"] == "completed"
        for item in workspace["demo_accounts"]
    )

    seeded_again = client.post("/api/v1/demo-accounts/seed")
    assert seeded_again.status_code == 201
    assert len(seeded_again.json()["demo_accounts"]) == 5

    evaluated = client.post("/api/v1/system-evaluations/run")
    assert evaluated.status_code == 201
    result = evaluated.json()["latest_run"]
    assert result["is_deterministic"] is True
    assert result["demo_account_count"] == 5
    assert result["total_tasks"] == 35
    assert result["passed_tasks"] == 35
    assert result["pass_rate"] == 100
    assert result["hallucination_rate"] == 0
    assert result["citation_correctness"] == 100
    assert result["task_completion_rate"] == 100
    assert result["estimated_cost_usd"] == 0
    assert len(result["metrics"]) == 7
    assert len(result["tasks"]) == 35

    listed = client.get("/api/v1/system-evaluation")
    assert listed.status_code == 200
    assert listed.json()["latest_run"]["id"] == result["id"]
