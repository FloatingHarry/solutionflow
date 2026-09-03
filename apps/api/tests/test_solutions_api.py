def create_account(client, name="Solution Test Account"):
    response = client.post(
        "/api/v1/accounts",
        json={
            "name": name,
            "website": "https://solution.example",
            "industry": "Logistics",
            "region": "Europe",
            "notes": "Reduce manual document and spreadsheet handoffs.",
        },
    )
    assert response.status_code == 201
    return response.json()


def approve_research(client, account_id):
    run = client.post(
        f"/api/v1/accounts/{account_id}/research-runs",
        json={"provider": "mock"},
    )
    assert run.status_code == 202
    approved = client.post(
        f"/api/v1/research-runs/{run.json()['id']}/review",
        json={"decision": "approve", "notes": "Evidence reviewed."},
    )
    assert approved.status_code == 200


def complete_discovery(client, account_id):
    approve_research(client, account_id)
    generated = client.post(
        f"/api/v1/accounts/{account_id}/discovery/generate",
        json={"max_hypotheses": 1},
    )
    assert generated.status_code == 201
    hypothesis = generated.json()[0]
    accepted = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/review",
        json={"decision": "accept", "notes": "Validate through customer discovery."},
    )
    assert accepted.status_code == 200
    question = accepted.json()["questions"][0]
    answered = client.post(
        f"/api/v1/discovery-questions/{question['id']}/answers",
        json={
            "answer_text": (
                "Manual shipping documents and spreadsheet handoffs add three days of delay."
            ),
            "respondent_name": "Demo Customer",
            "respondent_role": "Operations Director",
        },
    )
    assert answered.status_code == 201
    answer = answered.json()
    confirmed = client.post(
        f"/api/v1/opportunity-hypotheses/{hypothesis['id']}/confirm",
        json={
            "title": "Automate manual document and spreadsheet handoffs",
            "description": (
                "Operations needs validated document extraction and workflow automation."
            ),
            "business_impact": "Reduce processing delay and manual rework.",
            "success_metric": "Reduce processing lead time from three days to one day.",
            "constraints": "Keep EU data in-region and export to the finance spreadsheet.",
            "answer_ids": [answer["id"]],
        },
    )
    assert confirmed.status_code == 201
    need = confirmed.json()
    discovery_review = client.post(
        f"/api/v1/accounts/{account_id}/discovery/review",
        json={"decision": "approve", "notes": "Customer need and metric reviewed."},
    )
    assert discovery_review.status_code == 200
    return need


def test_demo_catalog_contains_four_structured_templates(client):
    response = client.get("/api/v1/solutions/catalog")

    assert response.status_code == 200
    catalog = response.json()
    assert len(catalog) == 4
    assert {item["name"] for item in catalog} == {
        "Enterprise Knowledge Assistant",
        "Customer Service Copilot",
        "Sales / Account Copilot",
        "Document Intelligence",
    }
    assert all(item["is_simulated"] is True for item in catalog)
    assert all(item["architecture"] for item in catalog)
    assert all(item["deployment_options"] for item in catalog)
    assert all(item["known_limitations"] for item in catalog)


def test_solution_matching_requires_approved_discovery(client):
    account = create_account(client)

    response = client.post(
        f"/api/v1/accounts/{account['id']}/solutions/matches",
        json={"top_per_need": 3},
    )

    assert response.status_code == 409
    assert "Approve customer discovery" in response.json()["detail"]


def test_solution_match_proposal_traceability_and_workflow(client):
    account = create_account(client)
    need = complete_discovery(client, account["id"])

    matched = client.post(
        f"/api/v1/accounts/{account['id']}/solutions/matches",
        json={"top_per_need": 4},
    )
    assert matched.status_code == 201
    matches = matched.json()
    assert len(matches) == 4
    assert matches[0]["template"]["name"] == "Document Intelligence"
    assert matches[0]["score"] > matches[-1]["score"]
    assert "spreadsheet" in matches[0]["matched_terms"]

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][3]["status"] == "in_progress"
    assert workflow["current_stage"] == "solution"

    proposal_response = client.post(
        f"/api/v1/accounts/{account['id']}/solution-proposals",
        json={
            "solution_template_id": matches[0]["template"]["id"],
            "need_ids": [need["id"]],
            "deployment_option": "eu_cloud",
        },
    )
    assert proposal_response.status_code == 201
    proposal = proposal_response.json()
    assert proposal["status"] == "draft"
    assert proposal["derived_needs"][0]["id"] == need["id"]
    assert proposal["template"]["name"] == "Document Intelligence"
    assert proposal["architecture"]
    assert proposal["required_data"]
    assert proposal["risks"]
    assert need["success_metric"] in proposal["success_metrics"]

    updated = client.patch(
        f"/api/v1/solution-proposals/{proposal['id']}",
        json={"title": "EU Document Intelligence workflow"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "EU Document Intelligence workflow"

    accepted = client.post(
        f"/api/v1/solution-proposals/{proposal['id']}/review",
        json={"decision": "accept", "notes": "Architecture and need mapping reviewed."},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    workflow = client.get(f"/api/v1/accounts/{account['id']}/workflow").json()
    assert workflow["stages"][3]["status"] == "completed"
    assert workflow["current_stage"] == "poc"

    workspace = client.get(f"/api/v1/accounts/{account['id']}/solutions").json()
    assert workspace["catalog_is_simulated"] is True
    assert workspace["proposals"][0]["derived_needs"][0]["id"] == need["id"]

    locked = client.post(
        f"/api/v1/accounts/{account['id']}/solutions/matches",
        json={"top_per_need": 1},
    )
    assert locked.status_code == 409
    assert locked.json()["detail"] == "An accepted solution is read-only"

    activities = client.get(f"/api/v1/accounts/{account['id']}/activities").json()["items"]
    event_types = {item["event_type"] for item in activities}
    assert "solution.matches_generated" in event_types
    assert "solution.proposal_created" in event_types
    assert "solution.proposal_accepted" in event_types


def test_proposal_requires_match_and_supported_deployment(client):
    account = create_account(client)
    need = complete_discovery(client, account["id"])
    catalog = client.get("/api/v1/solutions/catalog").json()
    service_template = next(item for item in catalog if item["name"] == "Customer Service Copilot")

    missing_match = client.post(
        f"/api/v1/accounts/{account['id']}/solution-proposals",
        json={
            "solution_template_id": service_template["id"],
            "need_ids": [need["id"]],
            "deployment_option": "saas_api",
        },
    )
    assert missing_match.status_code == 409
    assert "Generate solution matches" in missing_match.json()["detail"]

    matched = client.post(
        f"/api/v1/accounts/{account['id']}/solutions/matches",
        json={"top_per_need": 4},
    )
    assert matched.status_code == 201
    unsupported = client.post(
        f"/api/v1/accounts/{account['id']}/solution-proposals",
        json={
            "solution_template_id": service_template["id"],
            "need_ids": [need["id"]],
            "deployment_option": "private_on_premise",
        },
    )
    assert unsupported.status_code == 409
    assert "deployment is not supported" in unsupported.json()["detail"]


def test_archived_account_cannot_generate_solution_matches(client):
    account = create_account(client)
    complete_discovery(client, account["id"])
    archived = client.post(f"/api/v1/accounts/{account['id']}/archive")
    assert archived.status_code == 200

    response = client.post(
        f"/api/v1/accounts/{account['id']}/solutions/matches",
        json={"top_per_need": 3},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Archived account is read-only"
