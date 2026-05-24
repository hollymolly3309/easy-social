from __future__ import annotations

import pytest

from easy_social.extensions import db
from easy_social.models import PollVote, Post, User

from conftest import login, logout, register

pytestmark = pytest.mark.integration


def create_poll(client, question: str, *options: str):
    data = {
        "post_type": "poll",
        "body": question,
        "poll_option_1": options[0] if len(options) > 0 else "",
        "poll_option_2": options[1] if len(options) > 1 else "",
        "poll_option_3": options[2] if len(options) > 2 else "",
        "poll_option_4": options[3] if len(options) > 3 else "",
    }
    return client.post("/posts", data=data, follow_redirects=True)


def test_create_poll_post_via_route(client, app):
    register(client, "alice")
    response = create_poll(client, "Team lunch?", "Pizza", "Sushi")

    assert response.status_code == 200
    assert b"Team lunch?" in response.data
    with app.app_context():
        post = Post.query.filter_by(body="Team lunch?").one()
        assert post.poll is not None
        assert len(post.poll.options) == 2


def test_create_poll_rejects_single_option(client, app):
    register(client, "alice")
    response = create_poll(client, "Bad poll", "Only one")

    assert b"Polls must have between 2 and 4 options." in response.data
    with app.app_context():
        assert Post.query.filter_by(body="Bad poll").first() is None


def test_user_can_vote_and_see_results(client, app):
    register(client, "alice")
    create_poll(client, "Favorite color?", "Blue", "Green")
    logout(client)
    register(client, "bob")

    with app.app_context():
        post = Post.query.filter_by(body="Favorite color?").one()
        option_id = post.poll.options[0].id
        post_id = post.id

    response = client.post(
        f"/posts/{post_id}/vote",
        data={"option_id": option_id},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"100.0%" in response.data
    assert b"You voted on this poll." in response.data
    with app.app_context():
        bob = User.query.filter_by(username="bob").one()
        assert PollVote.query.filter_by(user_id=bob.id).count() == 1


def test_duplicate_vote_is_rejected(client, app):
    register(client, "alice")
    create_poll(client, "Snack?", "Chips", "Cookies")

    with app.app_context():
        post = Post.query.filter_by(body="Snack?").one()
        post_id = post.id
        first_option = post.poll.options[0].id
        second_option = post.poll.options[1].id

    client.post(f"/posts/{post_id}/vote", data={"option_id": first_option}, follow_redirects=True)
    response = client.post(
        f"/posts/{post_id}/vote",
        data={"option_id": second_option},
        follow_redirects=True,
    )

    assert b"You have already voted on this poll." in response.data
    with app.app_context():
        post = Post.query.filter_by(body="Snack?").one()
        assert PollVote.query.filter_by(poll_id=post.poll.id).count() == 1


def test_vote_on_non_poll_post_is_rejected(client, app):
    register(client, "alice")
    client.post("/posts", data={"body": "Plain post"}, follow_redirects=True)

    with app.app_context():
        post_id = Post.query.filter_by(body="Plain post").one().id

    response = client.post(
        f"/posts/{post_id}/vote",
        data={"option_id": 1},
        follow_redirects=True,
    )

    assert b"This post is not a poll." in response.data
