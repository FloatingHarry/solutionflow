from test_poc_api import accept_document_solution, create_account


def complete_poc(client, account_id):
    accept_document_solution(client, account_id)
    plan = client.post(f"/api/v1/accounts/{account_id}/poc-plans/generate").json()
    approved = client.post(
        f"/api/v1/poc-plans/{plan['id']}/review",
        json={"decision": "approve", "notes": "POC plan approved."},
    )
    assert approved.status_code == 200
    plan = approved.json()
    passing_values = [94, 76, 0.8, 4.5]
    for metric, actual in zip(plan["metrics"], passing_values, strict=True):
        response = client.patch(
            f"/api/v1/poc-metrics/{metric['id']}", json={"actual_value": actual}
        )
        assert response.status_code == 200
        plan = response.json()
    decision = client.post(
        f"/api/v1/poc-plans/{plan['id']}/decision",
        json={"decision": "proceed", "rationale": "All targets passed."},
    )
    assert decision.status_code == 200
    return decision.json()


def test_business_case_requires_completed_proceed_evaluation(client):
    account = create_account(client, "Business Case Prerequisite")

    response = client.post(f"/api/v1/accounts/{account['id']}/business-cases/generate")

    assert response.status_code == 409
    assert "Complete POC evaluation with a Proceed decision" in response.json()["detail"]


def test_business_case_generation_calculation_traceability_and_approval(client):
    account = create_account(client, "Business Case Flow")
    plan = complete_poc(client, account["id"])

    generated = client.post(f"/api/v1/accounts/{account['id']}/business-cases/generate")
    assert generated.status_code == 201
    case = generated.json()
    assert case["scenario_is_estimate"] is True
    assert case["status"] == "draft"
    assert case["currency"] == "EUR"
    assert case["current_monthly_cost"] == 16875
    assert case["estimated_new_labor_cost"] == 8437.5
    assert case["estimated_new_total_cost"] == 11237.5
    assert case["monthly_savings"] == 5637.5
    assert case["annual_savings"] == 67650
    assert case["estimated_first_year_roi_percent"] == 50.33
    assert case["payback_period_months"] == 7.98
    assert case["poc_plan"]["id"] == plan["id"]
    assert case["poc_plan"]["solution_proposal"]["derived_needs"]
    assert len(case["deployment_assessments"]) == 3
    assert {item["option"] for item in case["deployment_assessments"]} == {
        "saas_api",
        "eu_cloud",
        "private_on_premise",
    }
    assert "Scenario estimate only" in case["brief"]["roi_summary"]

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][6]["status"] == "in_progress"
    assert workflow["current_stage"] == "business_case"

    recalculated = client.patch(
        f"/api/v1/business-cases/{case['id']}/scenario",
        json={
            "number_employees": 40,
            "average_hourly_cost": 50,
            "current_time_per_task_minutes": 30,
            "tasks_per_employee_per_month": 15,
            "expected_time_reduction_percent": 60,
            "monthly_ai_cost": 3000,
            "implementation_cost": 50000,
        },
    )
    assert recalculated.status_code == 200
    case = recalculated.json()
    assert case["current_monthly_cost"] == 15000
    assert case["estimated_new_labor_cost"] == 6000
    assert case["estimated_new_total_cost"] == 9000
    assert case["monthly_savings"] == 6000
    assert case["annual_savings"] == 72000
    assert case["estimated_first_year_roi_percent"] == 44
    assert case["payback_period_months"] == 8.33
    assert "EUR 72,000" in case["brief"]["roi_summary"]

    deployment = client.patch(
        f"/api/v1/business-cases/{case['id']}/deployment",
        json={
            "recommended_deployment": "private_on_premise",
            "deployment_rationale": "Use private hosting after security and capacity validation.",
        },
    )
    assert deployment.status_code == 200
    case = deployment.json()
    assert case["recommended_deployment"] == "private_on_premise"
    assert "Private On Premise" in case["brief"]["deployment_summary"]

    brief = client.patch(
        f"/api/v1/account-briefs/{case['brief']['id']}",
        json={
            "executive_summary": (
                "The evidence chain, POC results, scenario economics, and deployment trade-offs "
                "support a controlled production planning phase."
            )
        },
    )
    assert brief.status_code == 200
    case = brief.json()
    assert case["brief"]["executive_summary"].startswith("The evidence chain")

    revision = client.post(
        f"/api/v1/business-cases/{case['id']}/review",
        json={"decision": "needs_revision", "notes": "Finance must validate assumptions."},
    )
    assert revision.status_code == 200
    assert revision.json()["status"] == "needs_revision"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][6]["status"] == "blocked"

    updated = client.patch(
        f"/api/v1/business-cases/{case['id']}/scenario",
        json={"implementation_cost": 48000},
    )
    assert updated.status_code == 200
    approved = client.post(
        f"/api/v1/business-cases/{case['id']}/review",
        json={
            "decision": "approve",
            "notes": "Finance assumptions and deployment trade-offs reviewed.",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][6]["status"] == "completed"
    assert workflow["stages"][7]["status"] == "not_started"
    assert workflow["current_stage"] == "deployment"

    activities = client.get(f"/api/v1/accounts/{account['id']}/activities").json()["items"]
    event_types = {item["event_type"] for item in activities}
    assert "business_case.generated" in event_types
    assert "business_case.scenario_updated" in event_types
    assert "business_case.deployment_updated" in event_types
    assert "business_case.brief_updated" in event_types
    assert "business_case.approved" in event_types


def test_zero_or_negative_savings_has_no_payback(client):
    account = create_account(client, "Negative Savings")
    complete_poc(client, account["id"])
    case = client.post(f"/api/v1/accounts/{account['id']}/business-cases/generate").json()

    response = client.patch(
        f"/api/v1/business-cases/{case['id']}/scenario",
        json={"expected_time_reduction_percent": 0, "monthly_ai_cost": 5000},
    )

    assert response.status_code == 200
    assert response.json()["monthly_savings"] == -5000
    assert response.json()["payback_period_months"] is None
    assert "not reached" in response.json()["brief"]["roi_summary"]


def test_approved_business_case_is_read_only(client):
    account = create_account(client, "Approved Business Case")
    complete_poc(client, account["id"])
    case = client.post(f"/api/v1/accounts/{account['id']}/business-cases/generate").json()
    approved = client.post(
        f"/api/v1/business-cases/{case['id']}/review",
        json={"decision": "approve", "notes": "Business case reviewed."},
    )
    assert approved.status_code == 200

    locked = client.patch(
        f"/api/v1/business-cases/{case['id']}/scenario",
        json={"number_employees": 99},
    )

    assert locked.status_code == 409
    assert "Only draft or revision business cases can be edited" in locked.json()["detail"]


def test_archived_account_cannot_generate_business_case(client):
    account = create_account(client, "Archived Business Case")
    complete_poc(client, account["id"])
    assert client.post(f"/api/v1/accounts/{account['id']}/archive").status_code == 200

    response = client.post(f"/api/v1/accounts/{account['id']}/business-cases/generate")

    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
