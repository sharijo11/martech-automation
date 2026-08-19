from app import app, execute_provider


def test_phase_3_1_health_shape():
    client = app.test_client()
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['phase'] == '3.1'


def test_provider_log_route_exists():
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert '/leads/<int:lead_id>/provider-logs' in rules


def test_legacy_maintenance_route_exists():
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert '/maintenance/legacy-sales-tasks/requeue' in rules
