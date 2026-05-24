from __future__ import annotations

import pytest

import time

from easy_social.captcha import CAPTCHA_CREATED_AT_KEY, CAPTCHA_TTL_SECONDS
from easy_social.extensions import db
from easy_social.models import User

pytestmark = pytest.mark.integration

TEST_CAPTCHA = "TEST1"


def test_register_succeeds_with_valid_captcha(client, app):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "password",
            "captcha": TEST_CAPTCHA,
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


def test_register_rejects_expired_captcha(client, app):
    client.get("/auth/register")
    with client.session_transaction() as sess:
        sess[CAPTCHA_CREATED_AT_KEY] = time.time() - CAPTCHA_TTL_SECONDS - 1

    response = client.post(
        "/auth/register",
        data={
            "username": "dave",
            "email": "dave@example.com",
            "password": "password",
            "captcha": "TEST1",
        },
        follow_redirects=True,
    )

    assert b"Invalid or expired CAPTCHA" in response.data
    with app.app_context():
        assert User.query.filter_by(username="dave").first() is None


def test_register_page_embeds_captcha_image(client):
    response = client.get("/auth/register")

    assert response.status_code == 200
    assert b'data:image/png;base64,' in response.data
