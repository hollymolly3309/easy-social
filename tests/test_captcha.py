from __future__ import annotations

import pytest

from easy_social.captcha import (
    CAPTCHA_CHARSET,
    CAPTCHA_LENGTH,
    CAPTCHA_SESSION_KEY,
    clear_captcha,
    generate_code,
    get_captcha,
    refresh_captcha,
    render_captcha_image,
    store_captcha,
    verify_captcha,
)

pytestmark = pytest.mark.unit


def test_generate_code_length_and_charset():
    code = generate_code()
    assert len(code) == CAPTCHA_LENGTH
    assert all(character in CAPTCHA_CHARSET for character in code)


def test_store_and_get_captcha():
    session = {}
    store_captcha(session, "ABCDE")
    assert get_captcha(session) == "ABCDE"
    assert session[CAPTCHA_SESSION_KEY] == "ABCDE"


def test_verify_captcha_accepts_correct_input():
    session = {}
    store_captcha(session, "ABCDE")
    assert verify_captcha(session, "ABCDE") is True


def test_verify_captcha_rejects_wrong_input():
    session = {}
    store_captcha(session, "ABCDE")
    assert verify_captcha(session, "WRONG") is False


def test_verify_captcha_rejects_missing_session_value():
    assert verify_captcha({}, "ABCDE") is False


def test_verify_captcha_ignores_case_and_whitespace():
    session = {}
    store_captcha(session, "AB12C")
    assert verify_captcha(session, " ab12c ") is True


def test_clear_captcha_removes_session_value():
    session = {}
    store_captcha(session, "ABCDE")
    clear_captcha(session)
    assert get_captcha(session) is None


def test_refresh_captcha_stores_new_code():
    session = {}
    code = refresh_captcha(session)
    assert code == get_captcha(session)


def test_refresh_captcha_uses_fixed_code_when_provided():
    session = {}
    code = refresh_captcha(session, fixed_code="TEST1")
    assert code == "TEST1"
    assert get_captcha(session) == "TEST1"


def test_render_captcha_image_returns_png_bytes():
    png_bytes = render_captcha_image("ABCDE")
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG")
    assert len(png_bytes) > 0
