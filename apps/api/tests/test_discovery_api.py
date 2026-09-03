def create_account(client, name="Discovery Test Account"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://discovery.example",
            "industry": "Industrial Services",
            "region": "Asia Pacific",
            "notes": "Validate service operations and measurable customer outcomes.",
        },
    )
    assert response.status_code == 201
    return response.json()


def approve_research(client, account_id):
    started = client.post(
        f"/api/v1/accounts/{account_id}/research-runs",
        json={"provider": "mock"},
    )
    assert started.status_code == 202
    reviewed = client.post(
        f"/api/v1/research-runs/{started.json()['id']}/review",
        json={"decision": "approve", "notes": "Research evidence reviewed."},
    )
    assert reviewed.status_code == 200
    return started.json()


def generate_and_accept(client, account_id):
    generated = client.post(
        f"/api/v1/accounts/{account_id}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert generated.status_code == 201
    hypothesis = generated.json()[0]
    reviewed = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/review",
        json={"decision": "accept", "notes": "Validate this with customer evidence."},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def test_hypothesis_generation_requires_approved_research(client):
    account = create_account(client)

    response = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/generate",
        json={"max_hypotheses": 1},
    )

    assert response.status_code == 409
    assert "Approve account research" in response.json()["detail"]


def test_discovery_traceability_and_workflow_progression(client):
    account = create_account(client)
    approve_research(client, account["id"])

    generated = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert generated.status_code == 201
    hypothesis = generated.json()[0]
    assert hypothesis["status"] == "need_validation"
    assert hypothesis["origin"] == "research_template"
    assert hypothesis["source_claim_id"]
    assert hypothesis["evidence"]
    assert len(hypothesis["questions"]) == 4

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][1]["status"] == "in_progress"

    reviewed = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/review",
        json={"decision": "accept", "notes": "Take this hypothesis into discovery."},
    )
    assert reviewed.status_code == 200
    accepted = reviewed.json()
    assert accepted["status"] == "user_accepted"

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][1]["status"] == "completed"
    assert workflow["stages"][2]["status"] == "in_progress"
    assert workflow["current_stage"] == "discovery"

    question = accepted["questions"][0]
    answered = client.post(
        f"/api/v1/discovery-questions/{question['id']}/answers",
        json={
            "answer_text": (
                "Planning takes three days and requires two manual spreadsheet handoffs."
            ),
            "respondent_name": "Jordan Lee",
            "respondent_role": "Operations Director",
        },
    )
    assert answered.status_code == 201
    answer = answered.json()

    confirmed = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/confirm",
        json={
            "title": "Reduce manual planning handoffs",
            "description": "Operations needs a faster, auditable planning workflow.",
            "business_impact": "Shorter planning cycles and fewer handoff errors.",
            "success_metric": "Cut planning lead time from three days to one day.",
            "constraints": "Keep an export compatible with the finance spreadsheet.",
            "answer_ids": [answer["id"]],
        },
    )
    assert confirmed.status_code == 201
    need = confirmed.json()
    assert need["supporting_answer_ids"] == [answer["id"]]

    workspace = client.get(f"/api/v1/accounts/{account['id']}/discovery").json()
    assert workspace["hypotheses"][0]["status"] == "confirmed"
    assert workspace["hypotheses"][0]["confirmed_need"]["id"] == need["id"]
    assert workspace["confirmed_needs"][0]["id"] == need["id"]

    approval = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/review",
        json={"decision": "approve", "notes": "Need and success metric confirmed."},
    )
    assert approval.status_code == 200
    assert approval.json()["decision"] == "approve"

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][2]["status"] == "completed"
    assert workflow["current_stage"] == "solution"

    activities = client.get(f"/api/v1/accounts/{account['id']}/activities").json()["items"]
    event_types = {item["event_type"] for item in activities}
    assert "discovery.need_confirmed" in event_types
    assert "discovery.approved" in event_types

    locked = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert locked.status_code == 409
    assert locked.json()["detail"] == "Approved customer discovery is read-only"


def test_question_crud_and_answered_question_protection(client):
    account = create_account(client)
    approve_research(client, account["id"])
    hypothesis = generate_and_accept(client, account["id"])

    created = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/questions",
        json={"question": "Who owns the current KPI?", "rationale": "Clarify ownership."},
    )
    assert created.status_code == 201
    question_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/discovery-questions/{question_id}",
        json={"question": "Who owns the current success KPI?"},
    )
    assert updated.status_code == 200
    assert updated.json()["question"] == "Who owns the current success KPI?"

    deleted = client.delete(f"/api/v1/discovery-questions/{question_id}")
    assert deleted.status_code == 204

    answered_question = hypothesis["questions"][0]
    answer = client.post(
        f"/api/v1/discovery-questions/{answered_question['id']}/answers",
        json={"answer_text": "The regional operations team owns it."},
    )
    assert answer.status_code == 201

    protected = client.delete(f"/api/v1/discovery-questions/{answered_question['id']}")
    assert protected.status_code == 409
    assert protected.json()["detail"] == "Answered questions cannot be deleted"


def test_discovery_review_requires_confirmed_need_and_can_request_revision(client):
    account = create_account(client)
    approve_research(client, account["id"])
    generate_and_accept(client, account["id"])

    premature = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/review",
        json={"decision": "approve", "notes": "Approve without a need."},
    )
    assert premature.status_code == 409
    assert "Confirm at least one customer need" in premature.json()["detail"]

    revision = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/review",
        json={"decision": "reject", "notes": "Quantify the success metric first."},
    )
    assert revision.status_code == 200

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][2]["status"] == "blocked"

    duplicate_revision = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/review",
        json={"decision": "reject", "notes": "Still needs revision."},
    )
    assert duplicate_revision.status_code == 409


def test_archived_account_cannot_generate_hypotheses(client):
    account = create_account(client)
    approve_research(client, account["id"])
    archived = client.post(f"/api/v1/accounts/{account['id']}/archive")
    assert archived.status_code == 200

    response = client.post(
        f"/api/v1/accounts/{account['id']}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
