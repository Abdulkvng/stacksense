"""
Flask server for StackSense dashboard.
"""

import os
import secrets
import json
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, Response
from sqlalchemy import Integer, desc, func

from stacksense.database import get_db_manager
from stacksense.database.models import Event, User, UserAPIKey
from stacksense.dashboard.security import EncryptionError, encrypt_secret, mask_secret
from stacksense.enterprise.monitoring import monitor

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def create_app(db_manager=None, debug=False):
    """
    Create Flask application for StackSense dashboard.

    Args:
        db_manager: DatabaseManager instance
        debug: Enable debug mode

    Returns:
        Flask application
    """
    app = Flask(
        __name__,
        static_folder=Path(__file__).parent / "static",
        template_folder=Path(__file__).parent / "templates",
    )
    app.config["DEBUG"] = debug
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("STACKSENSE_SECURE_COOKIES", "false").lower() == "true"
    )
    app.secret_key = os.getenv("STACKSENSE_SESSION_SECRET", "stacksense-dashboard-dev-secret")

    if not db_manager:
        db_manager = get_db_manager()

    # Development mode: auto-create test user
    DEV_MODE = os.getenv("STACKSENSE_DEV_MODE", "false").lower() == "true"
    if DEV_MODE:
        with db_manager.get_session() as session_db:
            test_user = session_db.query(User).filter(User.email == "test@stacksense.dev").first()
            if not test_user:
                test_user = User(
                    google_sub="dev-test-user",
                    email="test@stacksense.dev",
                    name="Test User",
                    avatar_url=None,
                    last_login_at=datetime.utcnow(),
                )
                session_db.add(test_user)
                session_db.flush()
                print(f"✅ Created test user: test@stacksense.dev (ID: {test_user.id})")

    def _google_oauth_config():
        return {
            "client_id": os.getenv("STACKSENSE_GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("STACKSENSE_GOOGLE_CLIENT_SECRET"),
            "redirect_uri": os.getenv("STACKSENSE_GOOGLE_REDIRECT_URI")
            or url_for("google_callback", _external=True),
        }

    def _google_oauth_ready() -> bool:
        config = _google_oauth_config()
        return bool(config["client_id"] and config["client_secret"])

    def _current_user(session_db):
        user_id = session.get("user_id")
        if not user_id:
            return None
        try:
            return (
                session_db.query(User)
                .filter(User.id == user_id, User.is_active.is_(True))
                .first()
            )
        except Exception as e:
            app.logger.error(f"Error fetching current user: {e}")
            return None

    def login_required(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            # Skip authentication in dev mode with auto-login
            if DEV_MODE and session.get("user_id"):
                return view_func(*args, **kwargs)

            user_id = session.get("user_id")
            if not user_id:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("login"))

            with db_manager.get_session() as session_db:
                user = _current_user(session_db)
                if not user:
                    session.clear()
                    if request.path.startswith("/api/"):
                        return jsonify({"error": "Session expired"}), 401
                    return redirect(url_for("login"))

            return view_func(*args, **kwargs)

        return wrapped

    @app.route("/")
    def root():
        return render_template("landing_v3.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """Render advanced dashboard."""
        return render_template("dashboard_v2.html")

    @app.route("/login")
    def login():
        """Render Google sign-in page."""
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            google_ready=_google_oauth_ready(),
            error_message=request.args.get("error"),
            dev_mode=DEV_MODE,
        )

    @app.route("/dev/login")
    def dev_login():
        """Development mode auto-login."""
        if not DEV_MODE:
            return redirect(url_for("login", error="Development mode not enabled"))

        with db_manager.get_session() as session_db:
            test_user = session_db.query(User).filter(User.email == "test@stacksense.dev").first()
            if not test_user:
                return redirect(url_for("login", error="Test user not found"))

            session.clear()
            session["user_id"] = test_user.id
            return redirect(url_for("dashboard"))

    @app.route("/auth/google")
    def google_auth():
        """Start Google OAuth flow."""
        if not _google_oauth_ready():
            return redirect(
                url_for(
                    "login",
                    error="Google OAuth is not configured. Set STACKSENSE_GOOGLE_CLIENT_ID and STACKSENSE_GOOGLE_CLIENT_SECRET.",
                )
            )

        config = _google_oauth_config()
        state = secrets.token_urlsafe(24)
        session["oauth_state"] = state

        query = urlencode(
            {
                "client_id": config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
                "access_type": "offline",
            }
        )

        return redirect(f"{GOOGLE_AUTH_URL}?{query}")

    @app.route("/auth/google/callback")
    def google_callback():
        """Complete Google OAuth and persist user account."""
        if request.args.get("error"):
            return redirect(url_for("login", error="Google sign-in was cancelled."))

        state = request.args.get("state")
        expected_state = session.pop("oauth_state", None)
        if not state or not expected_state or state != expected_state:
            return redirect(url_for("login", error="Invalid sign-in state. Please try again."))

        code = request.args.get("code")
        if not code:
            return redirect(url_for("login", error="Missing authorization code from Google."))

        config = _google_oauth_config()
        if not _google_oauth_ready():
            return redirect(url_for("login", error="Google OAuth is not configured."))

        try:
            token_response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "redirect_uri": config["redirect_uri"],
                    "grant_type": "authorization_code",
                },
                timeout=12,
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                return redirect(url_for("login", error="Unable to get Google access token."))

            user_response = requests.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=12,
            )
            user_response.raise_for_status()
            profile = user_response.json()
        except requests.RequestException:
            return redirect(url_for("login", error="Google sign-in failed. Please try again."))

        google_sub = profile.get("sub")
        email = profile.get("email")
        name = profile.get("name") or email
        avatar = profile.get("picture")

        if not google_sub or not email:
            return redirect(url_for("login", error="Google profile is missing required fields."))

        with db_manager.get_session() as session_db:
            user = session_db.query(User).filter(User.google_sub == google_sub).one_or_none()
            now = datetime.utcnow()

            if user is None:
                user = User(
                    google_sub=google_sub,
                    email=email,
                    name=name,
                    avatar_url=avatar,
                    last_login_at=now,
                )
                session_db.add(user)
                session_db.flush()
            else:
                user.email = email
                user.name = name
                user.avatar_url = avatar
                user.last_login_at = now
                session_db.flush()

            session.clear()
            session["user_id"] = user.id

        return redirect(url_for("dashboard"))

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        """Sign user out of dashboard."""
        session.clear()
        return redirect(url_for("login"))

    @app.route("/api/me")
    @login_required
    def get_me():
        """Return current signed in user."""
        with db_manager.get_session() as session_db:
            user = _current_user(session_db)
            if not user:
                session.clear()
                return jsonify({"error": "Session expired"}), 401

            return jsonify(
                {
                    "user": user.to_dict(),
                    "google_oauth_configured": _google_oauth_ready(),
                }
            )

    @app.route("/api/user/api-keys", methods=["GET"])
    @login_required
    def list_api_keys():
        """List API keys for the current user."""
        with db_manager.get_session() as session_db:
            user = _current_user(session_db)
            if not user:
                session.clear()
                return jsonify({"error": "Session expired"}), 401

            keys = (
                session_db.query(UserAPIKey)
                .filter(UserAPIKey.user_id == user.id)
                .order_by(desc(UserAPIKey.updated_at))
                .all()
            )
            return jsonify([key.to_dict() for key in keys])

    @app.route("/api/user/api-keys", methods=["POST"])
    @login_required
    def create_or_rotate_api_key():
        """Create or update an API key for the current user."""
        payload = request.get_json(silent=True) or {}

        provider = _normalize_provider(payload.get("provider"))
        label = str(payload.get("label") or "").strip()
        secret = str(payload.get("api_key") or "").strip()

        if not provider:
            return jsonify({"error": "Provider is required"}), 400
        if not secret:
            return jsonify({"error": "API key value is required"}), 400

        safe_label = label[:120] if label else provider.upper()

        try:
            encrypted = encrypt_secret(secret)
            hint = mask_secret(secret)
        except EncryptionError as exc:
            return jsonify({"error": str(exc)}), 500

        with db_manager.get_session() as session_db:
            user = _current_user(session_db)
            if not user:
                session.clear()
                return jsonify({"error": "Session expired"}), 401

            existing = (
                session_db.query(UserAPIKey)
                .filter(
                    UserAPIKey.user_id == user.id,
                    UserAPIKey.provider == provider,
                    UserAPIKey.label == safe_label,
                )
                .one_or_none()
            )

            if existing:
                existing.encrypted_key = encrypted
                existing.key_hint = hint
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                session_db.flush()
                return jsonify(existing.to_dict()), 200

            record = UserAPIKey(
                user_id=user.id,
                provider=provider,
                label=safe_label,
                encrypted_key=encrypted,
                key_hint=hint,
            )
            session_db.add(record)
            session_db.flush()
            return jsonify(record.to_dict()), 201

    @app.route("/api/user/api-keys/<int:key_id>", methods=["PUT"])
    @login_required
    def update_api_key(key_id: int):
        """Update label and/or rotate key value."""
        payload = request.get_json(silent=True) or {}
        new_label = str(payload.get("label") or "").strip()
        new_secret = str(payload.get("api_key") or "").strip()

        with db_manager.get_session() as session_db:
            user = _current_user(session_db)
            if not user:
                session.clear()
                return jsonify({"error": "Session expired"}), 401

            key_record = (
                session_db.query(UserAPIKey)
                .filter(UserAPIKey.id == key_id, UserAPIKey.user_id == user.id)
                .one_or_none()
            )

            if not key_record:
                return jsonify({"error": "API key not found"}), 404

            changed = False
            if new_label:
                safe_label = new_label[:120]
                duplicate = (
                    session_db.query(UserAPIKey)
                    .filter(
                        UserAPIKey.user_id == user.id,
                        UserAPIKey.provider == key_record.provider,
                        UserAPIKey.label == safe_label,
                        UserAPIKey.id != key_record.id,
                    )
                    .one_or_none()
                )
                if duplicate:
                    return jsonify({"error": "Another key already uses this label"}), 409

                key_record.label = safe_label
                changed = True

            if new_secret:
                try:
                    key_record.encrypted_key = encrypt_secret(new_secret)
                    key_record.key_hint = mask_secret(new_secret)
                    changed = True
                except EncryptionError as exc:
                    return jsonify({"error": str(exc)}), 500

            if not changed:
                return jsonify({"error": "No updates provided"}), 400

            key_record.updated_at = datetime.utcnow()
            session_db.flush()
            return jsonify(key_record.to_dict())

    @app.route("/api/user/api-keys/<int:key_id>", methods=["DELETE"])
    @login_required
    def delete_api_key(key_id: int):
        """Delete API key owned by current user."""
        with db_manager.get_session() as session_db:
            user = _current_user(session_db)
            if not user:
                session.clear()
                return jsonify({"error": "Session expired"}), 401

            key_record = (
                session_db.query(UserAPIKey)
                .filter(UserAPIKey.id == key_id, UserAPIKey.user_id == user.id)
                .one_or_none()
            )

            if not key_record:
                return jsonify({"error": "API key not found"}), 404

            session_db.delete(key_record)
            return jsonify({"success": True})

    @app.route("/api/metrics/summary")
    @login_required
    def get_metrics_summary():
        """Get metrics summary."""
        try:
            timeframe = request.args.get("timeframe", "24h")

            with db_manager.get_session() as session_db:
                delta = _parse_timeframe(timeframe)
                cutoff = datetime.utcnow() - delta

                stats = (
                    session_db.query(
                        func.count(Event.id).label("total_calls"),
                        func.sum(Event.total_tokens).label("total_tokens"),
                        func.sum(Event.cost).label("total_cost"),
                        func.avg(Event.latency).label("avg_latency"),
                        func.sum(func.cast(~Event.success, Integer)).label("error_count"),
                    )
                    .filter(Event.timestamp >= cutoff)
                    .first()
                )

                total_calls = stats.total_calls or 0
                total_tokens = stats.total_tokens or 0
                total_cost = float(stats.total_cost or 0.0)
                avg_latency = float(stats.avg_latency or 0.0)
                error_count = stats.error_count or 0
                error_rate = (error_count / total_calls * 100) if total_calls > 0 else 0.0

                return jsonify(
                    {
                        "total_calls": total_calls,
                        "total_tokens": total_tokens,
                        "total_cost": round(total_cost, 4),
                        "avg_cost_per_call": (
                            round(total_cost / total_calls, 4) if total_calls > 0 else 0
                        ),
                        "avg_latency": round(avg_latency, 2),
                        "error_rate": round(error_rate, 2),
                    }
                )
        except Exception as exc:  # pragma: no cover
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/metrics/cost-breakdown")
    @login_required
    def get_cost_breakdown():
        """Get cost breakdown by provider."""
        try:
            timeframe = request.args.get("timeframe", "24h")
            delta = _parse_timeframe(timeframe)
            cutoff = datetime.utcnow() - delta

            with db_manager.get_session() as session_db:
                breakdown = (
                    session_db.query(Event.provider, func.sum(Event.cost).label("total_cost"))
                    .filter(Event.timestamp >= cutoff)
                    .group_by(Event.provider)
                    .all()
                )

                result = {provider: float(cost) for provider, cost in breakdown}
                return jsonify(result)
        except Exception as exc:  # pragma: no cover
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/metrics/detailed")
    @login_required
    def get_detailed_metrics():
        """Get detailed telemetry metrics."""
        try:
            timeframe = request.args.get("timeframe", "24h")
            delta = _parse_timeframe(timeframe)
            cutoff = datetime.utcnow() - delta

            with db_manager.get_session() as session_db:
                # Model breakdown
                model_breakdown = (
                    session_db.query(
                        Event.model,
                        func.count(Event.id).label("count"),
                        func.sum(Event.cost).label("total_cost"),
                        func.sum(Event.total_tokens).label("total_tokens")
                    )
                    .filter(Event.timestamp >= cutoff)
                    .group_by(Event.model)
                    .all()
                )

                # Provider breakdown with details
                provider_breakdown = (
                    session_db.query(
                        Event.provider,
                        func.count(Event.id).label("count"),
                        func.sum(Event.cost).label("total_cost"),
                        func.avg(Event.latency).label("avg_latency"),
                        func.sum(Event.total_tokens).label("total_tokens")
                    )
                    .filter(Event.timestamp >= cutoff)
                    .group_by(Event.provider)
                    .all()
                )

                # Top expensive calls
                expensive_calls = (
                    session_db.query(Event)
                    .filter(Event.timestamp >= cutoff)
                    .order_by(desc(Event.cost))
                    .limit(5)
                    .all()
                )

                # Token usage stats
                token_stats = (
                    session_db.query(
                        func.sum(Event.input_tokens).label("total_prompt_tokens"),
                        func.sum(Event.output_tokens).label("total_completion_tokens"),
                        func.avg(Event.input_tokens).label("avg_prompt_tokens"),
                        func.avg(Event.output_tokens).label("avg_completion_tokens")
                    )
                    .filter(Event.timestamp >= cutoff)
                    .first()
                )

                return jsonify({
                    "models": [
                        {
                            "model": row.model,
                            "calls": row.count,
                            "cost": float(row.total_cost or 0),
                            "tokens": int(row.total_tokens or 0)
                        }
                        for row in model_breakdown
                    ],
                    "providers": [
                        {
                            "provider": row.provider,
                            "calls": row.count,
                            "cost": float(row.total_cost or 0),
                            "avg_latency": float(row.avg_latency or 0),
                            "tokens": int(row.total_tokens or 0)
                        }
                        for row in provider_breakdown
                    ],
                    "expensive_calls": [
                        {
                            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                            "model": event.model,
                            "provider": event.provider,
                            "cost": float(event.cost or 0),
                            "tokens": int(event.total_tokens or 0),
                            "latency": float(event.latency or 0)
                        }
                        for event in expensive_calls
                    ],
                    "token_stats": {
                        "total_prompt_tokens": int(token_stats.total_prompt_tokens or 0),
                        "total_completion_tokens": int(token_stats.total_completion_tokens or 0),
                        "avg_prompt_tokens": float(token_stats.avg_prompt_tokens or 0),
                        "avg_completion_tokens": float(token_stats.avg_completion_tokens or 0)
                    } if token_stats else {}
                })

        except Exception as exc:  # pragma: no cover
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/metrics/usage-over-time")
    @login_required
    def get_usage_over_time():
        """Get usage metrics over time."""
        try:
            timeframe = request.args.get("timeframe", "24h")
            interval = request.args.get("interval", "1h")

            delta = _parse_timeframe(timeframe)
            cutoff = datetime.utcnow() - delta

            with db_manager.get_session() as session_db:
                events = (
                    session_db.query(Event)
                    .filter(Event.timestamp >= cutoff)
                    .order_by(Event.timestamp)
                    .all()
                )

                buckets = {}
                for event in events:
                    bucket_key = _get_time_bucket(event.timestamp, interval)
                    if bucket_key not in buckets:
                        buckets[bucket_key] = {"calls": 0, "tokens": 0, "cost": 0.0}
                    buckets[bucket_key]["calls"] += 1
                    buckets[bucket_key]["tokens"] += event.total_tokens or 0
                    buckets[bucket_key]["cost"] += event.cost or 0.0

                result = [{"timestamp": key, **value} for key, value in sorted(buckets.items())]
                return jsonify(result)
        except Exception as exc:  # pragma: no cover
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/events/recent")
    @login_required
    def get_recent_events():
        """Get recent events."""
        try:
            limit = int(request.args.get("limit", 50))

            with db_manager.get_session() as session_db:
                events = session_db.query(Event).order_by(desc(Event.timestamp)).limit(limit).all()

                return jsonify([event.to_dict() for event in events])
        except Exception as exc:  # pragma: no cover
            return jsonify({"error": str(exc)}), 500

    # ==================== LIVE MONITORING ENDPOINTS ====================

    @app.route("/metrics")
    def prometheus_metrics():
        """Expose Prometheus metrics in exposition format."""
        metrics_data = monitor.get_metrics()
        return Response(metrics_data, mimetype="text/plain; version=0.0.4")

    @app.route("/api/live/health")
    @login_required
    def get_health():
        """Get system health status."""
        try:
            metrics_dict = monitor.get_metrics_dict()
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "components": metrics_dict.get("health_checks", {}),
                "prometheus_available": metrics_dict.get("prometheus_available", False)
            })
        except Exception as exc:
            return jsonify({
                "status": "unhealthy",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat()
            }), 500

    @app.route("/api/live/metrics")
    @login_required
    def get_live_metrics():
        """Get current live monitoring metrics as JSON."""
        try:
            metrics_dict = monitor.get_metrics_dict()

            # Get recent alerts
            severity = request.args.get("severity")
            limit = int(request.args.get("limit", 100))
            alerts = monitor.get_alerts(limit=limit, severity=severity)

            return jsonify({
                "timestamp": datetime.utcnow().isoformat(),
                "prometheus_available": metrics_dict.get("prometheus_available", False),
                "alerts": alerts,
                "alerts_count": len(alerts),
                "health_checks": metrics_dict.get("health_checks", {})
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/live/stream")
    @login_required
    def live_metrics_stream():
        """
        Server-Sent Events stream for real-time metrics updates.

        Usage from frontend:
            const eventSource = new EventSource('/api/live/stream');
            eventSource.onmessage = (event) => {
                const metrics = JSON.parse(event.data);
                updateDashboard(metrics);
            };
        """
        def generate_metrics():
            """Generate metrics stream."""
            while True:
                try:
                    metrics_dict = monitor.get_metrics_dict()
                    alerts = monitor.get_alerts(limit=10)

                    data = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "prometheus_available": metrics_dict.get("prometheus_available", False),
                        "recent_alerts": alerts,
                        "alerts_count": metrics_dict.get("alerts_count", 0),
                        "health_checks": metrics_dict.get("health_checks", {})
                    }

                    yield f"data: {json.dumps(data)}\n\n"
                    time.sleep(5)  # Update every 5 seconds

                except GeneratorExit:
                    break
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                    time.sleep(5)

        return Response(
            generate_metrics(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    @app.route("/api/live/alerts", methods=["GET"])
    @login_required
    def get_live_alerts():
        """Get current alerts."""
        try:
            severity = request.args.get("severity")
            limit = int(request.args.get("limit", 100))
            alerts = monitor.get_alerts(limit=limit, severity=severity)

            return jsonify({
                "alerts": alerts,
                "count": len(alerts)
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/live/alerts", methods=["DELETE"])
    @login_required
    def clear_live_alerts():
        """Clear all alerts."""
        try:
            monitor.clear_alerts()
            return jsonify({"success": True, "message": "All alerts cleared"})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ==================== ENTERPRISE METRICS ENDPOINTS ====================

    @app.route("/api/enterprise/stats")
    @login_required
    def get_enterprise_stats():
        """Get enterprise feature statistics."""
        try:
            with db_manager.get_session() as session_db:
                user = _current_user(session_db)
                if not user:
                    return jsonify({"error": "User not found"}), 404

                from stacksense.database.models import (
                    RoutingRule, Budget, SLAConfig, AuditLog,
                    AgentRun, Policy
                )

                # Count configured features
                routing_rules_count = session_db.query(RoutingRule).filter(
                    RoutingRule.user_id == user.id,
                    RoutingRule.is_active == True
                ).count()

                budgets_count = session_db.query(Budget).filter(
                    Budget.user_id == user.id,
                    Budget.is_active == True
                ).count()

                sla_configs_count = session_db.query(SLAConfig).filter(
                    SLAConfig.user_id == user.id,
                    SLAConfig.is_active == True
                ).count()

                policies_count = session_db.query(Policy).filter(
                    Policy.user_id == user.id,
                    Policy.is_active == True
                ).count()

                audit_events_count = session_db.query(AuditLog).filter(
                    AuditLog.user_id == user.id
                ).count()

                # Get active agent runs
                active_agent_runs = session_db.query(AgentRun).filter(
                    AgentRun.user_id == user.id,
                    AgentRun.status == "running"
                ).count()

                # Get loop detections
                loop_detections = session_db.query(AgentRun).filter(
                    AgentRun.user_id == user.id,
                    AgentRun.loop_detected == True
                ).count()

                # Calculate cost optimization metrics
                from sqlalchemy import func
                from stacksense.database.models import Event

                # Get events for analysis
                total_events = session_db.query(Event).count()

                # Simple waste estimation (events with high cost per token)
                if total_events > 0:
                    avg_cost_per_token = session_db.query(
                        func.avg(Event.cost / func.nullif(Event.total_tokens, 0))
                    ).filter(Event.total_tokens > 0).scalar() or 0.0

                    # Find inefficient calls (2x+ above average cost per token)
                    threshold = avg_cost_per_token * 2
                    wasteful_events = session_db.query(
                        func.sum(Event.cost)
                    ).filter(
                        Event.total_tokens > 0,
                        (Event.cost / Event.total_tokens) > threshold
                    ).scalar() or 0.0

                    total_cost = session_db.query(func.sum(Event.cost)).scalar() or 0.0
                    waste_percentage = (wasteful_events / total_cost * 100) if total_cost > 0 else 0.0
                else:
                    wasteful_events = 0.0
                    waste_percentage = 0.0

                return jsonify({
                    "routing_rules": routing_rules_count,
                    "budgets": budgets_count,
                    "sla_configs": sla_configs_count,
                    "policies": policies_count,
                    "audit_events": audit_events_count,
                    "active_agent_runs": active_agent_runs,
                    "loop_detections": loop_detections,
                    "estimated_waste": round(wasteful_events, 2),
                    "waste_percentage": round(waste_percentage, 1)
                })

        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return app


def _normalize_provider(provider: str) -> str:
    """Normalize provider labels from user input."""
    cleaned = (provider or "").strip().lower().replace(" ", "-")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_"
    return "".join(ch for ch in cleaned if ch in allowed)[:80]


def _parse_timeframe(timeframe: str) -> timedelta:
    """Parse timeframe string to timedelta."""
    try:
        unit = timeframe[-1]
        value = int(timeframe[:-1])
    except (TypeError, ValueError):
        return timedelta(hours=24)

    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)
    if unit == "w":
        return timedelta(weeks=value)
    return timedelta(hours=24)


def _get_time_bucket(timestamp: datetime, interval: str) -> str:
    """Get time bucket for timestamp."""
    if interval == "1h":
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
    elif interval == "1d":
        timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    return timestamp.isoformat()


def run_server(host="127.0.0.1", port=5000, debug=False, db_manager=None):
    """
    Run the dashboard server.

    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
        db_manager: DatabaseManager instance
    """
    app = create_app(db_manager=db_manager, debug=debug)
    print(f"StackSense Dashboard running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
