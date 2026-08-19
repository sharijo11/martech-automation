from datetime import datetime, timedelta
from types import SimpleNamespace

from app import task_is_due


def test_task_is_due_when_due_at_is_none():
    task = SimpleNamespace(due_at=None)
    assert task_is_due(task, datetime(2026, 8, 17, 12, 0, 0)) is True


def test_task_is_due_for_past_time():
    now = datetime(2026, 8, 17, 12, 0, 0)
    task = SimpleNamespace(due_at=now - timedelta(minutes=1))
    assert task_is_due(task, now) is True


def test_task_is_not_due_for_future_time():
    now = datetime(2026, 8, 17, 12, 0, 0)
    task = SimpleNamespace(due_at=now + timedelta(minutes=1))
    assert task_is_due(task, now) is False
