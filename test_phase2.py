from app import automation_rules, calculate_score, categorise_score, validate_lead


def test_hot_lead_score_and_rules():
    lead = {
        "first_name": "Amara",
        "last_name": "Jones",
        "email": "amara@example.com",
        "company": "Example FinTech",
        "job_title": "Head of Growth",
        "company_size": 600,
        "source": "demo_request",
        "intent": "pricing",
    }
    assert calculate_score(lead) == 95
    assert categorise_score(95) == "hot"
    rules = automation_rules("hot")
    assert len(rules) == 2
    assert rules[0]["action_type"] == "priority_sales_follow_up"
    assert rules[1]["channel"] == "email"


def test_warm_lead_rules():
    rules = automation_rules("warm")
    assert {rule["action_type"] for rule in rules} == {"nurture_sequence", "sales_follow_up"}


def test_cold_lead_rules():
    rules = automation_rules("cold")
    assert len(rules) == 1
    assert rules[0]["action_type"] == "low_priority_nurture"


def test_validation_rejects_bad_email():
    valid, error = validate_lead({"first_name": "A", "last_name": "B", "email": "not-an-email"})
    assert valid is False
    assert error == "Invalid email address"
