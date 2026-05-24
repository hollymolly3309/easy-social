from __future__ import annotations

import pytest

from easy_social.extensions import db
from easy_social.models import User

pytestmark = pytest.mark.integration


def test_register_succeeds_with_valid_captcha(client, app):
    client.get("/auth/register")
    with client.session_transaction() as sess:
        captcha = sess["captcha_answer"]

    response = client.post(
        "/auth/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password",
            "captcha": captcha,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Feed" in response.data
    with app.app_context():
        assert User.query.filter_by(username="alice").one().email == "alice@example.com"


def test_register_rejects_invalid_captcha(client, app):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password": "password",
            "captcha": "WRONG",
        },
        follow_redirects=True,
    )

    assert b"Invalid or expired CAPTCHA" in response.data
    with app.app_context():
        assert User.query.filter_by(username="bob").first() is None


def test_register_rejects_missing_captcha(client, app):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "username": "carol",
            "email": "carol@example.com",
            "password": "password",
        },
        follow_redirects=True,
    )

    assert b"Invalid or expired CAPTCHA" in response.data
    with app.app_context():
        assert User.query.filter_by(username="carol").first() is None


def test_captcha_image_endpoint_returns_png(client):
    client.get("/auth/register")
    response = client.get("/auth/captcha-image")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
