from app import app, email_payload, hubspot_contact_payload


def test_health_phase3():
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["phase"] == 3


def test_hubspot_payload_shape():
    class Lead:
        email = "person@example.com"
        first_name = "Test"
        last_name = "Person"
        company = "Demo Ltd"
        job_title = "Marketing Director"
    payload = hubspot_contact_payload(Lead())
    assert payload["properties"]["email"] == "person@example.com"
    assert payload["properties"]["firstname"] == "Test"


def test_email_payload_shape():
    class Lead:
        first_name = "Test"
        last_name = "Person"
        company = "Demo Ltd"
        score = 95
        job_title = "Marketing Director"
        intent = "pricing"
        email = "person@example.com"
    payload = email_payload(Lead())
    assert "Hot lead" in payload["subject"]
    assert payload["to"]
