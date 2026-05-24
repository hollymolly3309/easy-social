from __future__ import annotations

import pytest

from easy_social.captcha import (
    CAPTCHA_CREATED_AT_KEY,
    CAPTCHA_CHARSET,
    CAPTCHA_LENGTH,
    CAPTCHA_SESSION_KEY,
    CAPTCHA_TTL_SECONDS,
    captcha_digest,
    captcha_image_b64,
    clear_captcha,
    generate_code,
    get_captcha_hash,
    refresh_captcha,
    render_captcha_image,
    store_captcha,
    verify_captcha,
)

pytestmark = pytest.mark.unit

TEST_SECRET = "test-secret"


def test_generate_code_length_and_charset():
    code = generate_code()
    assert len(code) == CAPTCHA_LENGTH
    assert all(character in CAPTCHA_CHARSET for character in code)


def test_store_captcha_persists_hmac_not_plaintext():
    session = {}
    store_captcha(session, "ABCDE", secret=TEST_SECRET)
    assert session[CAPTCHA_SESSION_KEY] == captcha_digest("ABCDE", TEST_SECRET)
    assert session[CAPTCHA_SESSION_KEY] != "ABCDE"


def test_verify_captcha_accepts_correct_input():
    session = {}
    store_captcha(session, "ABCDE", secret=TEST_SECRET)
    assert verify_captcha(session, "ABCDE", secret=TEST_SECRET) is True


def test_verify_captcha_rejects_wrong_input():
    session = {}
    store_captcha(session, "ABCDE", secret=TEST_SECRET)
    assert verify_captcha(session, "WRONG", secret=TEST_SECRET) is False


def test_verify_captcha_rejects_missing_session_value():
    assert verify_captcha({}, "ABCDE", secret=TEST_SECRET) is False


def test_verify_captcha_ignores_case_and_whitespace():
    session = {}
    store_captcha(session, "AB12C", secret=TEST_SECRET)
    assert verify_captcha(session, " ab12c ", secret=TEST_SECRET) is True


def test_clear_captcha_removes_session_value():
    session = {}
    store_captcha(session, "ABCDE", secret=TEST_SECRET)
    clear_captcha(session)
    assert get_captcha_hash(session) is None


def test_refresh_captcha_stores_verifiable_hash():
    session = {}
    code, image_b64 = refresh_captcha(session, secret=TEST_SECRET)
    assert verify_captcha(session, code, secret=TEST_SECRET) is True
    assert image_b64


def test_refresh_captcha_uses_fixed_code_when_provided():
    session = {}
    code, _ = refresh_captcha(session, secret=TEST_SECRET, fixed_code="TEST1")
    assert code == "TEST1"
    assert verify_captcha(session, "TEST1", secret=TEST_SECRET) is True


def test_verify_captcha_rejects_expired_code(monkeypatch):
    session = {}
    store_captcha(session, "ABCDE", secret=TEST_SECRET)
    created_at = session[CAPTCHA_CREATED_AT_KEY]
    monkeypatch.setattr("easy_social.captcha.time.time", lambda: created_at + CAPTCHA_TTL_SECONDS + 1)
    assert verify_captcha(session, "ABCDE", secret=TEST_SECRET) is False


def test_render_captcha_image_returns_png_bytes():
    png_bytes = render_captcha_image("ABCDE")
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG")
    assert len(png_bytes) > 0


def test_captcha_image_b64_is_valid_base64_png():
    image_b64 = captcha_image_b64("ABCDE")
    assert image_b64
    assert image_b64.startswith("iVBOR")
