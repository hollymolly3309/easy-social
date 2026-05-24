from __future__ import annotations

import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

CAPTCHA_SESSION_KEY = "captcha_answer"
CAPTCHA_LENGTH = 5
CAPTCHA_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_code(length: int = CAPTCHA_LENGTH) -> str:
    return "".join(random.choices(CAPTCHA_CHARSET, k=length))


def store_captcha(session, code: str) -> None:
    session[CAPTCHA_SESSION_KEY] = code


def get_captcha(session) -> str | None:
    return session.get(CAPTCHA_SESSION_KEY)


def clear_captcha(session) -> None:
    session.pop(CAPTCHA_SESSION_KEY, None)


def verify_captcha(session, user_input: str) -> bool:
    expected = get_captcha(session)
    if not expected:
        return False
    return user_input.strip().upper() == expected.strip().upper()


def refresh_captcha(session, *, fixed_code: str | None = None) -> str:
    code = fixed_code or generate_code()
    store_captcha(session, code)
    return code


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
