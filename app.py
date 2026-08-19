from datetime import datetime, timedelta
import hashlib
import hmac
import json
import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

load_dotenv()

app = Flask(__name__)

DB_USER = os.getenv("DB_USER", "martech_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "martech_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3307")
DB_NAME = os.getenv("DB_NAME", "martech_automation")
APP_PORT = int(os.getenv("APP_PORT", "5001"))

INTEGRATION_MODE = os.getenv("INTEGRATION_MODE", "test").lower()  # test | live
HUBSPOT_ACCESS_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
SALES_NOTIFICATION_TO = os.getenv("SALES_NOTIFICATION_TO", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me-before-live")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {
        "ssl": {
            "ca": os.getenv("DB_SSL_CA", "/etc/ssl/cert.pem")
        }
    }
}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    company = db.Column(db.String(255), nullable=True)
    job_title = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(100), nullable=False, default="website")
    company_size = db.Column(db.Integer, nullable=True)
    intent = db.Column(db.String(50), nullable=False, default="general")
    score = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(20), nullable=False, default="cold")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tasks = db.relationship("AutomationTask", backref="lead", lazy=True, cascade="all, delete-orphan")
    events = db.relationship("AutomationEvent", backref="lead", lazy=True, cascade="all, delete-orphan")
    provider_logs = db.relationship("ProviderLog", backref="lead", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "company": self.company,
            "job_title": self.job_title,
            "source": self.source,
            "company_size": self.company_size,
            "intent": self.intent,
            "score": self.score,
            "category": self.category,
            "created_at": iso(self.created_at),
        }


class AutomationTask(db.Model):
    __tablename__ = "automation_tasks"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)
    action_type = db.Column(db.String(100), nullable=False)
    channel = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    priority = db.Column(db.String(20), nullable=False, default="normal")
    due_at = db.Column(db.DateTime, nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    max_attempts = db.Column(db.Integer, nullable=False, default=3)
    last_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "action_type": self.action_type,
            "channel": self.channel,
            "status": self.status,
            "priority": self.priority,
            "due_at": iso(self.due_at),
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "completed_at": iso(self.completed_at),
        }


class AutomationEvent(db.Model):
    __tablename__ = "automation_events"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("automation_tasks.id"), nullable=True, index=True)
    event_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "created_at": iso(self.created_at),
        }


class ProviderLog(db.Model):
    __tablename__ = "provider_logs"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("automation_tasks.id"), nullable=True, index=True)
    provider = db.Column(db.String(50), nullable=False)
    operation = db.Column(db.String(100), nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    external_id = db.Column(db.String(255), nullable=True)
    http_status = db.Column(db.Integer, nullable=True)
    request_payload = db.Column(db.Text, nullable=True)
    response_payload = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "task_id": self.task_id,
            "provider": self.provider,
            "operation": self.operation,
            "mode": self.mode,
            "status": self.status,
            "external_id": self.external_id,
            "http_status": self.http_status,
            "error_message": self.error_message,
            "created_at": iso(self.created_at),
        }


def iso(value):
    return value.isoformat() + "Z" if value else None


def safe_json(value):
    try:
        return json.dumps(value, default=str)[:10000]
    except Exception:
        return str(value)[:10000]


def validate_lead(data):
    required = ["first_name", "last_name", "email"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"

    email = str(data.get("email", "")).strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Invalid email address"

    company_size = data.get("company_size")
    if company_size is not None:
        try:
            if int(company_size) < 0:
                return False, "company_size must be 0 or greater"
        except (TypeError, ValueError):
            return False, "company_size must be a whole number"

    return True, None


def calculate_score(data):
    score = 0
    if data.get("company"):
        score += 10
    if data.get("job_title"):
        score += 10

    size = int(data.get("company_size") or 0)
    if size >= 1000:
        score += 30
    elif size >= 250:
        score += 20
    elif size >= 50:
        score += 10

    score += {
        "demo_request": 25,
        "webinar": 15,
        "paid_search": 15,
        "organic_search": 10,
        "social": 5,
        "website": 5,
    }.get(str(data.get("source", "")).lower(), 0)

    score += {
        "buying": 35,
        "pricing": 30,
        "demo": 25,
        "comparison": 20,
        "research": 10,
        "general": 5,
    }.get(str(data.get("intent", "general")).lower(), 0)

    return min(score, 100)


def categorise_score(score):
    if score >= 80:
        return "hot"
    if score >= 50:
        return "warm"
    return "cold"


def automation_rules(category):
    now = datetime.utcnow()
    if category == "hot":
        return [
            {"action_type": "priority_sales_follow_up", "channel": "hubspot", "priority": "high", "due_at": now},
            {"action_type": "hot_lead_notification", "channel": "email", "priority": "high", "due_at": now},
        ]
    if category == "warm":
        return [
            {"action_type": "crm_sync", "channel": "hubspot", "priority": "normal", "due_at": now},
            {"action_type": "nurture_sequence", "channel": "email", "priority": "normal", "due_at": now},
        ]
    return [
        {"action_type": "crm_sync", "channel": "hubspot", "priority": "low", "due_at": now},
    ]


def add_event(lead_id, event_type, message, status="info", task_id=None):
    event = AutomationEvent(
        lead_id=lead_id,
        task_id=task_id,
        event_type=event_type,
        status=status,
        message=message,
    )
    db.session.add(event)
    return event


def add_provider_log(lead_id, task_id, provider, operation, status, request_payload=None,
                     response_payload=None, external_id=None, http_status=None, error_message=None):
    log = ProviderLog(
        lead_id=lead_id,
        task_id=task_id,
        provider=provider,
        operation=operation,
        mode=INTEGRATION_MODE,
        status=status,
        external_id=external_id,
        http_status=http_status,
        request_payload=safe_json(request_payload) if request_payload is not None else None,
        response_payload=safe_json(response_payload) if response_payload is not None else None,
        error_message=error_message,
    )
    db.session.add(log)
    return log


def create_automation_for_lead(lead):
    tasks = []
    add_event(lead.id, "lead_created", f"Lead {lead.email} was captured by the API.", "success")
    add_event(lead.id, "lead_scored", f"Lead scored {lead.score}/100 and categorised as {lead.category}.", "success")

    for rule in automation_rules(lead.category):
        task = AutomationTask(
            lead_id=lead.id,
            action_type=rule["action_type"],
            channel=rule["channel"],
            priority=rule["priority"],
            due_at=rule["due_at"],
            status="pending",
        )
        db.session.add(task)
        db.session.flush()
        tasks.append(task)
        add_event(lead.id, "task_created", f"Created {task.action_type} via {task.channel}.", "success", task.id)
    return tasks


def task_is_due(task, now=None):
    now = now or datetime.utcnow()
    return task.due_at is None or task.due_at <= now


def hubspot_contact_payload(lead):
    properties = {
        "email": lead.email,
        "firstname": lead.first_name,
        "lastname": lead.last_name,
    }
    if lead.company:
        properties["company"] = lead.company
    if lead.job_title:
        properties["jobtitle"] = lead.job_title
    return {"properties": properties}


def sync_to_hubspot(task):
    lead = task.lead
    payload = hubspot_contact_payload(lead)

    # Keep simulated behaviour when not in live mode
    if INTEGRATION_MODE != "live":
        fake_id = f"test-hubspot-{lead.id}"
        add_provider_log(
            lead.id,
            task.id,
            "hubspot",
            "create_contact",
            "success",
            payload,
            {"id": fake_id, "test_mode": True},
            fake_id,
            200,
        )
        return True, fake_id, None

    if not HUBSPOT_ACCESS_TOKEN:
        return False, None, "HUBSPOT_ACCESS_TOKEN is not configured"

    base_url = "https://api.hubapi.com/crm/v3/objects/contacts"

    headers = {
        "Authorization": f"Bearer {HUBSPOT_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        # 1. Try to update an existing HubSpot contact using email
        email_identifier = requests.utils.quote(lead.email, safe="")
        update_url = f"{base_url}/{email_identifier}?idProperty=email"

        response = requests.patch(
            update_url,
            headers=headers,
            json=payload,
            timeout=HTTP_TIMEOUT,
        )

        body = response.json() if response.content else {}

        # Contact exists: update succeeded
        if 200 <= response.status_code < 300:
            external_id = str(body.get("id", "")) or None

            add_provider_log(
                lead.id,
                task.id,
                "hubspot",
                "update_contact",
                "success",
                payload,
                body,
                external_id,
                response.status_code,
            )

            return True, external_id, None

        # 2. Contact doesn't exist: create it
        if response.status_code == 404:
            create_response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=HTTP_TIMEOUT,
            )

            create_body = (
                create_response.json()
                if create_response.content
                else {}
            )

            if 200 <= create_response.status_code < 300:
                external_id = str(create_body.get("id", "")) or None

                add_provider_log(
                    lead.id,
                    task.id,
                    "hubspot",
                    "create_contact",
                    "success",
                    payload,
                    create_body,
                    external_id,
                    create_response.status_code,
                )

                return True, external_id, None

            error = (
                create_body.get("message")
                or f"HubSpot returned HTTP {create_response.status_code}"
            )

            add_provider_log(
                lead.id,
                task.id,
                "hubspot",
                "create_contact",
                "failed",
                payload,
                create_body,
                http_status=create_response.status_code,
                error_message=error,
            )

            return False, None, error

        # PATCH failed for another reason
        error = (
            body.get("message")
            or f"HubSpot returned HTTP {response.status_code}"
        )

        add_provider_log(
            lead.id,
            task.id,
            "hubspot",
            "update_contact",
            "failed",
            payload,
            body,
            http_status=response.status_code,
            error_message=error,
        )

        return False, None, error

    except requests.RequestException as exc:
        error = f"HubSpot request failed: {exc}"

        add_provider_log(
            lead.id,
            task.id,
            "hubspot",
            "sync_contact",
            "failed",
            payload,
            error_message=error,
        )

        return False, None, error


def email_payload(lead):
    subject = f"Hot lead: {lead.first_name} {lead.last_name} ({lead.score}/100)"
    html = (
        f"<h2>New hot lead</h2>"
        f"<p><strong>{lead.first_name} {lead.last_name}</strong> from {lead.company or 'Unknown company'} "
        f"has scored <strong>{lead.score}/100</strong>.</p>"
        f"<p>Role: {lead.job_title or 'Not provided'}<br>Intent: {lead.intent}<br>Email: {lead.email}</p>"
    )
    return {
        "from": RESEND_FROM_EMAIL or "MarTech Demo <onboarding@resend.dev>",
        "to": [SALES_NOTIFICATION_TO or "delivered@resend.dev"],
        "subject": subject,
        "html": html,
    }


def send_email(task):
    lead = task.lead
    payload = email_payload(lead)

    if INTEGRATION_MODE != "live":
        fake_id = f"test-email-{task.id}"
        add_provider_log(lead.id, task.id, "resend", "send_email", "success", payload,
                         {"id": fake_id, "test_mode": True}, fake_id, 200)
        return True, fake_id, None

    if not RESEND_API_KEY:
        return False, None, "RESEND_API_KEY is not configured"
    if not RESEND_FROM_EMAIL or not SALES_NOTIFICATION_TO:
        return False, None, "RESEND_FROM_EMAIL and SALES_NOTIFICATION_TO must be configured in live mode"

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post("https://api.resend.com/emails", headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        body = response.json() if response.content else {}
        if 200 <= response.status_code < 300:
            external_id = str(body.get("id", "")) or None
            add_provider_log(lead.id, task.id, "resend", "send_email", "success", payload, body,
                             external_id, response.status_code)
            return True, external_id, None
        error = body.get("message") or body.get("name") or f"Resend returned HTTP {response.status_code}"
        add_provider_log(lead.id, task.id, "resend", "send_email", "failed", payload, body,
                         http_status=response.status_code, error_message=error)
        return False, None, error
    except requests.RequestException as exc:
        error = f"Resend request failed: {exc}"
        add_provider_log(lead.id, task.id, "resend", "send_email", "failed", payload,
                         error_message=error)
        return False, None, error


def execute_provider(task):
    if task.channel == "hubspot":
        return sync_to_hubspot(task)
    if task.channel == "email":
        return send_email(task)
    if task.channel == "sales_task":
        # Backward compatibility for Phase 2 records. Phase 2 sales tasks were
        # internal/mock actions, so Phase 3.1 safely records a compatibility
        # completion rather than calling a real external provider.
        external_id = f"legacy-sales-task-{task.id}"
        add_provider_log(
            task.lead_id, task.id, "internal", "legacy_sales_task_compat",
            "success",
            {"action_type": task.action_type, "channel": task.channel},
            {"message": "Legacy Phase 2 sales task accepted by Phase 3.1 compatibility handler"},
            external_id, 200,
        )
        return True, external_id, None
    return False, None, f"Unsupported channel: {task.channel}"


def execute_task(task, enforce_due=True):
    if task.status == "completed":
        return task, False, "Task is already completed"
    if task.status == "failed" and task.attempts >= task.max_attempts:
        return task, False, "Task has reached its maximum retry attempts"
    if enforce_due and not task_is_due(task):
        return task, False, f"Task is not due until {iso(task.due_at)}"

    task.attempts += 1
    task.updated_at = datetime.utcnow()
    add_event(task.lead_id, "task_started", f"Attempt {task.attempts} started for {task.action_type}.", "info", task.id)

    success, external_id, error = execute_provider(task)
    if success:
        task.status = "completed"
        task.last_error = None
        task.completed_at = datetime.utcnow()
        add_event(task.lead_id, "task_completed",
                  f"{task.channel} action completed" + (f" ({external_id})" if external_id else "") + ".",
                  "success", task.id)
        return task, True, None

    task.status = "failed"
    task.last_error = (error or "Provider execution failed")[:500]
    add_event(task.lead_id, "task_failed", task.last_error, "failed", task.id)
    return task, False, task.last_error


def create_lead_record(data):
    is_valid, error = validate_lead(data)
    if not is_valid:
        return None, None, error, 400

    score = calculate_score(data)
    category = categorise_score(score)
    lead = Lead(
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        email=data["email"].strip().lower(),
        company=data.get("company"),
        job_title=data.get("job_title"),
        source=data.get("source", "website"),
        company_size=int(data["company_size"]) if data.get("company_size") is not None else None,
        intent=data.get("intent", "general"),
        score=score,
        category=category,
    )
    try:
        db.session.add(lead)
        db.session.flush()
        tasks = create_automation_for_lead(lead)
        db.session.commit()
        return lead, tasks, None, 201
    except IntegrityError:
        db.session.rollback()
        return None, None, "A lead with this email already exists", 409
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Database error while creating lead")
        return None, None, "Database error", 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "martech-automation-api",
        "phase": "3.1",
        "integration_mode": INTEGRATION_MODE,
        "providers": {
            "hubspot_configured": bool(HUBSPOT_ACCESS_TOKEN),
            "resend_configured": bool(RESEND_API_KEY),
            "webhook_secret_default": WEBHOOK_SECRET == "change-me-before-live",
        },
    }), 200


@app.route("/leads", methods=["POST"])
def create_lead():
    data = request.get_json(silent=True) or {}
    lead, tasks, error, status = create_lead_record(data)
    if error:
        return jsonify({"error": error}), status
    return jsonify({
        "message": "Lead created and Phase 3.1 integration tasks generated",
        "lead": lead.to_dict(),
        "automation": {"task_count": len(tasks), "tasks": [task.to_dict() for task in tasks]},
    }), 201


@app.route("/webhooks/leads", methods=["POST"])
def inbound_lead_webhook():
    supplied_secret = request.headers.get("X-MarTech-Webhook-Secret", "")
    if not hmac.compare_digest(supplied_secret, WEBHOOK_SECRET):
        return jsonify({"error": "Invalid webhook secret"}), 401

    data = request.get_json(silent=True) or {}
    lead, tasks, error, status = create_lead_record(data)
    if error:
        return jsonify({"error": error}), status
    add_event(lead.id, "webhook_received", "Lead accepted through authenticated inbound webhook.", "success")
    db.session.commit()
    return jsonify({"message": "Webhook lead accepted", "lead": lead.to_dict(), "task_count": len(tasks)}), 201


@app.route("/webhooks/test-signature", methods=["POST"])
def signed_test_webhook():
    raw = request.get_data()
    supplied = request.headers.get("X-MarTech-Signature", "")
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "Invalid signature"}), 401
    return jsonify({"status": "accepted", "verified": True}), 200


@app.route("/leads", methods=["GET"])
def list_leads():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return jsonify({"count": len(leads), "leads": [lead.to_dict() for lead in leads]}), 200


@app.route("/leads/<int:lead_id>/automation", methods=["GET"])
def lead_automation_history(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    tasks = AutomationTask.query.filter_by(lead_id=lead_id).order_by(AutomationTask.created_at.asc()).all()
    events = AutomationEvent.query.filter_by(lead_id=lead_id).order_by(AutomationEvent.created_at.asc()).all()
    logs = ProviderLog.query.filter_by(lead_id=lead_id).order_by(ProviderLog.created_at.asc()).all()
    return jsonify({
        "lead": lead.to_dict(),
        "summary": {
            "tasks_total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "completed": sum(1 for t in tasks if t.status == "completed"),
            "failed": sum(1 for t in tasks if t.status == "failed"),
            "provider_calls": len(logs),
        },
        "tasks": [t.to_dict() for t in tasks],
        "events": [e.to_dict() for e in events],
        "provider_logs": [l.to_dict() for l in logs],
    }), 200


@app.route("/automation/tasks", methods=["GET"])
def list_tasks():
    status = request.args.get("status")
    query = AutomationTask.query
    if status:
        query = query.filter_by(status=status)
    tasks = query.order_by(AutomationTask.created_at.desc()).all()
    return jsonify({"count": len(tasks), "tasks": [t.to_dict() for t in tasks]}), 200


@app.route("/automations/process", methods=["POST"])
def process_automations():
    payload = request.get_json(silent=True) or {}
    try:
        limit = int(payload.get("limit", 50))
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be a whole number"}), 400
    if limit < 1 or limit > 500:
        return jsonify({"error": "limit must be between 1 and 500"}), 400

    now = datetime.utcnow()
    tasks = (
        AutomationTask.query
        .filter(AutomationTask.status == "pending")
        .filter((AutomationTask.due_at.is_(None)) | (AutomationTask.due_at <= now))
        .order_by(AutomationTask.due_at.asc(), AutomationTask.created_at.asc())
        .limit(limit)
        .all()
    )
    results, completed, failed = [], 0, 0
    for task in tasks:
        task, success, error = execute_task(task, enforce_due=True)
        completed += int(success)
        failed += int(not success)
        results.append({"task_id": task.id, "lead_id": task.lead_id, "channel": task.channel,
                        "status": task.status, "attempts": task.attempts, "error": error})
    db.session.commit()
    return jsonify({
        "message": "Due Phase 3.1 integration tasks processed",
        "integration_mode": INTEGRATION_MODE,
        "processed": len(results),
        "completed": completed,
        "failed": failed,
        "results": results,
    }), 200


@app.route("/automation/tasks/<int:task_id>/retry", methods=["POST"])
def retry_task(task_id):
    task = db.get_or_404(AutomationTask, task_id)
    if task.status != "failed":
        return jsonify({"error": "Only failed tasks can be retried", "task": task.to_dict()}), 409
    if task.attempts >= task.max_attempts:
        return jsonify({"error": "Maximum retry attempts reached", "task": task.to_dict()}), 409
    task.status = "pending"
    task.last_error = None
    add_event(task.lead_id, "task_retry_queued", f"Retry queued for {task.action_type}.", "info", task.id)
    task, success, error = execute_task(task, enforce_due=False)
    db.session.commit()
    if success:
        return jsonify({"message": "Automation task retry completed", "task": task.to_dict()}), 200
    return jsonify({"error": error, "task": task.to_dict()}), 503


@app.route("/provider-logs", methods=["GET"])
def provider_logs():
    logs = ProviderLog.query.order_by(ProviderLog.created_at.desc()).limit(200).all()
    return jsonify({"count": len(logs), "logs": [l.to_dict() for l in logs]}), 200


@app.route("/leads/<int:lead_id>/provider-logs", methods=["GET"])
def lead_provider_logs(lead_id):
    lead = db.get_or_404(Lead, lead_id)
    logs = (
        ProviderLog.query
        .filter_by(lead_id=lead_id)
        .order_by(ProviderLog.created_at.asc())
        .all()
    )
    return jsonify({
        "lead_id": lead.id,
        "email": lead.email,
        "count": len(logs),
        "logs": [log.to_dict() for log in logs],
    }), 200


@app.route("/maintenance/legacy-sales-tasks/requeue", methods=["POST"])
def requeue_legacy_sales_tasks():
    tasks = (
        AutomationTask.query
        .filter(AutomationTask.channel == "sales_task")
        .filter(AutomationTask.status == "failed")
        .all()
    )
    requeued = []
    skipped = []
    for task in tasks:
        if task.attempts >= task.max_attempts:
            skipped.append(task.id)
            continue
        task.status = "pending"
        task.last_error = None
        task.due_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        add_event(
            task.lead_id,
            "legacy_task_requeued",
            "Legacy Phase 2 sales task requeued for Phase 3.1 compatibility processing.",
            "info",
            task.id,
        )
        requeued.append(task.id)
    db.session.commit()
    return jsonify({
        "message": "Legacy sales_task maintenance complete",
        "requeued": requeued,
        "skipped_max_attempts": skipped,
        "count": len(requeued),
    }), 200


@app.route("/integrations/status", methods=["GET"])
def integrations_status():
    return jsonify({
        "mode": INTEGRATION_MODE,
        "hubspot": {"configured": bool(HUBSPOT_ACCESS_TOKEN), "provider": "HubSpot CRM"},
        "email": {"configured": bool(RESEND_API_KEY), "provider": "Resend",
                  "from_configured": bool(RESEND_FROM_EMAIL), "recipient_configured": bool(SALES_NOTIFICATION_TO)},
        "webhook": {"configured": WEBHOOK_SECRET != "change-me-before-live"},
    }), 200


def initialise_database():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    initialise_database()
    app.run(host="0.0.0.0", port=APP_PORT, debug=True)
