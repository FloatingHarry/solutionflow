def create_account(client, name="POC Test Account"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://poc.example",
            "industry": "Logistics",
            "region": "Europe",
            "notes": "Validate document workflow automation.",
        },
    )
    assert response.status_code == 201
    return response.json()


def accept_document_solution(client, account_id):
    run = client.post(
        f"/api/v1/accounts/{account_id}/research-runs", json={"provider": "mock"}
    )
    assert run.status_code == 202
    assert (
        client.post(
            f"/api/v1/research-runs/{run.json()['id']}/review",
            json={"decision": "approve", "notes": "Evidence reviewed."},
        ).status_code
        == 200
    )
    generated = client.post(
        f"/api/v1/accounts/{account_id}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert generated.status_code == 201
    hypothesis = generated.json()[0]
    accepted = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/review",
        json={"decision": "accept", "notes": "Validate with the customer."},
    )
    assert accepted.status_code == 200
    question = accepted.json()["questions"][0]
    answer = client.post(
        f"/api/v1/discovery-questions/{question['id']}/answers",
        json={
            "answer_text": "Shipping document handoffs add three days of delay.",
            "respondent_name": "Customer",
            "respondent_role": "Operations Director",
        },
    )
    assert answer.status_code == 201
    need = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/confirm",
        json={
            "title": "Automate document handoffs",
            "description": "Operations needs document extraction and validation automation.",
            "business_impact": "Reduce processing delay and manual rework.",
            "success_metric": "Reduce processing lead time from three days to one day.",
            "constraints": "Keep EU data in-region.",
            "answer_ids": [answer.json()["id"]],
        },
    )
    assert need.status_code == 201
    assert (
        client.post(
            f"/api/v1/accounts/{account_id}/discovery/review",
            json={"decision": "approve", "notes": "Customer need reviewed."},
        ).status_code
        == 200
    )
    matches = client.post(
        f"/api/v1/accounts/{account_id}/solutions/matches",
        json={"top_per_need": 4},
    )
    assert matches.status_code == 201
    document_match = next(
        item for item in matches.json() if item["template"]["slug"] == "document-intelligence"
    )
    proposal = client.post(
        f"/api/v1/accounts/{account_id}/solution-proposals",
        json={
            "solution_template_id": document_match["template"]["id"],
            "need_ids": [need.json()["id"]],
            "deployment_option": "eu_cloud",
        },
    )
    assert proposal.status_code == 201
    reviewed = client.post(
        f"/api/v1/solution-proposals/{proposal.json()['id']}/review",
        json={"decision": "accept", "notes": "Solution approved for POC."},
    )
    assert reviewed.status_code == 200
    return reviewed.json(), need.json()


def test_poc_generation_requires_an_accepted_solution(client):
    account = create_account(client)

    response = client.post(f"/api/v1/accounts/{account['id']}/poc-plans/generate")

    assert response.status_code == 409
    assert "Accept a solution proposal" in response.json()["detail"]


def test_poc_evaluation_iterate_and_proceed_flow(client):
    account = create_account(client)
    proposal, need = accept_document_solution(client, account["id"])

    generated = client.post(f"/api/v1/accounts/{account['id']}/poc-plans/generate")
    assert generated.status_code == 201
    plan = generated.json()
    assert plan["status"] == "draft"
    assert plan["timeline_days"] == 14
    assert plan["solution_proposal"]["id"] == proposal["id"]
    assert plan["solution_proposal"]["derived_needs"][0]["id"] == need["id"]
    assert [metric["metric_key"] for metric in plan["metrics"]] == [
        "field_extraction_accuracy",
        "straight_through_processing",
        "processing_lead_time",
        "human_rating",
    ]

    updated = client.patch(
        f"/api/v1/poc-plans/{plan['id']}",
        json={"timeline_days": 18, "scope": "Validate 200 representative documents."},
    )
    assert updated.status_code == 200
    assert updated.json()["timeline_days"] == 18

    approved = client.post(
        f"/api/v1/poc-plans/{plan['id']}/review",
        json={"decision": "approve", "notes": "Scope, data, and metrics approved."},
    )
    assert approved.status_code == 200
    plan = approved.json()
    assert plan["status"] == "approved"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][4]["status"] == "completed"
    assert workflow["stages"][5]["status"] == "in_progress"
    assert workflow["current_stage"] == "evaluation"

    actual_values = [94, 76, 1.2, 4.5]
    for metric, actual in zip(plan["metrics"], actual_values, strict=True):
        result = client.patch(
            f"/api/v1/poc-metrics/{metric['id']}",
            json={"actual_value": actual, "notes": "Measured on the holdout set."},
        )
        assert result.status_code == 200
        plan = result.json()
    lead_time = next(
        metric for metric in plan["metrics"] if metric["metric_key"] == "processing_lead_time"
    )
    assert lead_time["result_status"] == "fail"

    iterate = client.post(
        f"/api/v1/poc-plans/{plan['id']}/decision",
        json={"decision": "iterate", "rationale": "Lead time is above target."},
    )
    assert iterate.status_code == 200
    assert iterate.json()["decisions"][0]["decision"] == "iterate"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][5]["status"] == "blocked"

    corrected = client.patch(
        f"/api/v1/poc-metrics/{lead_time['id']}",
        json={"actual_value": 0.8, "notes": "Retested after queue optimization."},
    )
    assert corrected.status_code == 200
    assert next(
        metric
        for metric in corrected.json()["metrics"]
        if metric["metric_key"] == "processing_lead_time"
    )["result_status"] == "pass"
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][5]["status"] == "in_progress"

    proceeded = client.post(
        f"/api/v1/poc-plans/{plan['id']}/decision",
        json={
            "decision": "proceed",
            "rationale": "All evaluation targets pass on the approved holdout set.",
        },
    )
    assert proceeded.status_code == 200
    assert [item["decision"] for item in proceeded.json()["decisions"]] == [
        "proceed",
        "iterate",
    ]
    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][5]["status"] == "completed"
    assert workflow["current_stage"] == "business_case"

    activities = client.get(f"/api/v1/accounts/{account['id']}/activities").json()["items"]
    event_types = {item["event_type"] for item in activities}
    assert "poc.plan_generated" in event_types
    assert "poc.plan_approved" in event_types
    assert "poc.decision_iterate" in event_types
    assert "poc.decision_proceed" in event_types


def test_decision_requires_all_metric_results(client):
    account = create_account(client)
    accept_document_solution(client, account["id"])
    plan = client.post(f"/api/v1/accounts/{account['id']}/poc-plans/generate").json()
    approved = client.post(
        f"/api/v1/poc-plans/{plan['id']}/review",
        json={"decision": "approve", "notes": "Ready to evaluate."},
    )
    assert approved.status_code == 200

    response = client.post(
        f"/api/v1/poc-plans/{plan['id']}/decision",
        json={"decision": "proceed", "rationale": "Proceed."},
    )

    assert response.status_code == 409
    assert "Record actual values for every metric" in response.json()["detail"]


def test_approved_targets_and_completed_evaluation_are_read_only(client):
    account = create_account(client)
    accept_document_solution(client, account["id"])
    plan = client.post(f"/api/v1/accounts/{account['id']}/poc-plans/generate").json()
    plan = client.post(
        f"/api/v1/poc-plans/{plan['id']}/review",
        json={"decision": "approve", "notes": "Ready to evaluate."},
    ).json()

    locked_target = client.patch(
        f"/api/v1/poc-metrics/{plan['metrics'][0]['id']}",
        json={"target_value": 95},
    )
    assert locked_target.status_code == 409
    assert "targets are locked" in locked_target.json()["detail"]

    passing_values = [94, 76, 0.8, 4.5]
    for metric, actual in zip(plan["metrics"], passing_values, strict=True):
        plan = client.patch(
            f"/api/v1/poc-metrics/{metric['id']}", json={"actual_value": actual}
        ).json()
    assert (
        client.post(
            f"/api/v1/poc-plans/{plan['id']}/decision",
            json={"decision": "proceed", "rationale": "Targets passed."},
        ).status_code
        == 200
    )

    locked_result = client.patch(
        f"/api/v1/poc-metrics/{plan['metrics'][0]['id']}", json={"actual_value": 90}
    )
    assert locked_result.status_code == 409
    assert "completed evaluation is read-only" in locked_result.json()["detail"]


def test_archived_account_cannot_generate_poc_plan(client):
    account = create_account(client)
    accept_document_solution(client, account["id"])
    assert client.post(f"/api/v1/accounts/{account['id']}/archive").status_code == 200

    response = client.post(f"/api/v1/accounts/{account['id']}/poc-plans/generate")

    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
