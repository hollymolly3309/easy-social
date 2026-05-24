from __future__ import annotations

import pytest

from easy_social.extensions import db
from easy_social.models import PollVote, User
from easy_social.polls import (
    cast_vote,
    create_poll_post,
    normalize_poll_options,
    poll_results,
    validate_poll_options,
)

pytestmark = pytest.mark.unit


def make_user(username: str) -> User:
    user = User(username=username, email=f"{username}@example.com")
    user.set_password("password")
    return user


def test_normalize_poll_options_strips_and_skips_empty():
    assert normalize_poll_options([" Pizza ", "", "  ", "Pasta"]) == ["Pizza", "Pasta"]


def test_validate_poll_options_accepts_two_to_four():
    validate_poll_options(["A", "B"])
    validate_poll_options(["A", "B", "C", "D"])


def test_validate_poll_options_rejects_too_few():
    with pytest.raises(ValueError, match="between 2 and 4"):
        validate_poll_options(["Only one"])


def test_validate_poll_options_rejects_too_many():
    with pytest.raises(ValueError, match="between 2 and 4"):
        validate_poll_options(["A", "B", "C", "D", "E"])


def test_create_poll_post_persists_options(app):
    with app.app_context():
        user = make_user("alice")
        db.session.add(user)
        db.session.commit()

        post = create_poll_post(user, "Lunch?", ["Pizza", "Sushi"])
        db.session.commit()

        assert post.is_poll is True
        assert len(post.poll.options) == 2
        assert [option.text for option in post.poll.options] == ["Pizza", "Sushi"]


def test_cast_vote_records_choice(app):
    with app.app_context():
        user = make_user("alice")
        db.session.add(user)
        db.session.commit()

        post = create_poll_post(user, "Pick one", ["A", "B"])
        db.session.commit()
        option_id = post.poll.options[0].id

        cast_vote(post.poll, user, option_id)
        db.session.commit()

        assert PollVote.query.filter_by(poll_id=post.poll.id, user_id=user.id).count() == 1


def test_cast_vote_rejects_duplicate_vote(app):
    with app.app_context():
        user = make_user("alice")
        db.session.add(user)
        db.session.commit()

        post = create_poll_post(user, "Pick one", ["A", "B"])
        db.session.commit()
        first_option = post.poll.options[0].id
        second_option = post.poll.options[1].id

        cast_vote(post.poll, user, first_option)
        db.session.commit()

        with pytest.raises(ValueError, match="already voted"):
            cast_vote(post.poll, user, second_option)


def test_cast_vote_rejects_invalid_option(app):
    with app.app_context():
        user = make_user("alice")
        db.session.add(user)
        db.session.commit()

        post = create_poll_post(user, "Pick one", ["A", "B"])
        db.session.commit()

        with pytest.raises(ValueError, match="Invalid poll option"):
            cast_vote(post.poll, user, 99999)


def test_poll_results_calculates_percentages(app):
    with app.app_context():
        author = make_user("alice")
        voter = make_user("bob")
        db.session.add_all([author, voter])
        db.session.commit()

        post = create_poll_post(author, "Pick one", ["A", "B"])
        db.session.commit()

        cast_vote(post.poll, voter, post.poll.options[0].id)
        db.session.commit()

        results = poll_results(post.poll)
        assert results[0]["votes"] == 1
        assert results[0]["percentage"] == 100.0
        assert results[1]["votes"] == 0
        assert results[1]["percentage"] == 0.0
