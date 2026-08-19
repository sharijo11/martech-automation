from app import calculate_score, categorise_score


def test_hot_lead():
    data = {
        'company': 'OakNorth',
        'job_title': 'Marketing Director',
        'company_size': 1200,
        'source': 'demo_request',
        'intent': 'buying',
    }
    score = calculate_score(data)
    assert score == 100
    assert categorise_score(score) == 'hot'


def test_cold_lead():
    data = {
        'source': 'social',
        'intent': 'general',
    }
    score = calculate_score(data)
    assert score == 10
    assert categorise_score(score) == 'cold'
