from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from .captcha import clear_captcha, get_captcha, refresh_captcha, render_captcha_image, verify_captcha
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _fixed_captcha_code() -> str | None:
    return current_app.config.get("CAPTCHA_FIXED_CODE")


def _render_register():
    refresh_captcha(session, fixed_code=_fixed_captcha_code())
    return render_template("auth/register.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    if request.method == "POST":
        captcha_input = request.form.get("captcha", "").strip()
        if not verify_captcha(session, captcha_input):
            clear_captcha(session)
            flash("Invalid or expired CAPTCHA. Please try again.", "error")
            return _render_register()

        clear_captcha(session)

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not username or not email or not password:
            error = "Username, email, and password are required."
        elif len(username) > 40:
            error = "Username must be 40 characters or fewer."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif User.query.filter_by(email=email).first():
            error = "That email is already registered."

        if error:
            flash(error, "error")
            return _render_register()

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("social.feed"))

    return _render_register()


@bp.get("/captcha-image")
def captcha_image():
    code = get_captcha(session)
    if not code:
        code = refresh_captcha(session, fixed_code=_fixed_captcha_code())

    response = Response(render_captcha_image(code), mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == username_or_email)
            | (User.email == username_or_email.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("social.feed"))

        flash("Invalid username/email or password.", "error")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
