from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import random
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_SESSION_KEY = "captcha_hash"
CAPTCHA_CREATED_AT_KEY = "captcha_created_at"
CAPTCHA_TTL_SECONDS = 600
CAPTCHA_LENGTH = 5
CAPTCHA_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_code(length: int = CAPTCHA_LENGTH) -> str:
    return "".join(secrets.choice(CAPTCHA_CHARSET) for _ in range(length))


def captcha_digest(code: str, secret: str) -> str:
    normalized = code.strip().upper()
    return hmac.new(secret.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def store_captcha(session, code: str, *, secret: str) -> None:
    session[CAPTCHA_SESSION_KEY] = captcha_digest(code, secret)
    session[CAPTCHA_CREATED_AT_KEY] = time.time()


def captcha_is_expired(session, *, max_age: int = CAPTCHA_TTL_SECONDS) -> bool:
    created_at = session.get(CAPTCHA_CREATED_AT_KEY)
    if created_at is None:
        return True
    return time.time() - created_at > max_age


def get_captcha_hash(session) -> str | None:
    return session.get(CAPTCHA_SESSION_KEY)


def clear_captcha(session) -> None:
    session.pop(CAPTCHA_SESSION_KEY, None)
    session.pop(CAPTCHA_CREATED_AT_KEY, None)


def verify_captcha(session, user_input: str, *, secret: str, max_age: int = CAPTCHA_TTL_SECONDS) -> bool:
    if captcha_is_expired(session, max_age=max_age):
        return False
    expected = get_captcha_hash(session)
    if not expected:
        return False
    actual = captcha_digest(user_input, secret)
    return hmac.compare_digest(expected, actual)


def refresh_captcha(session, *, secret: str, fixed_code: str | None = None) -> tuple[str, str]:
    code = fixed_code or generate_code()
    store_captcha(session, code, secret=secret)
    return code, captcha_image_b64(code)


def captcha_image_b64(code: str) -> str:
    return base64.b64encode(render_captcha_image(code)).decode("ascii")


def render_captcha_image(code: str) -> bytes:
    width, height = 160, 48
    image = Image.new("RGB", (width, height), color=(247, 247, 244))
    draw = ImageDraw.Draw(image)

    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=(200, 206, 213), width=1)

    font = ImageFont.load_default()
    spacing = width // (len(code) + 1)
    for index, character in enumerate(code):
        x = spacing * (index + 1) - 6
        y = random.randint(10, 18)
        draw.text((x, y), character, fill=(28, 35, 43), font=font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
