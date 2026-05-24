from __future__ import annotations

from easy_social.extensions import db
from easy_social.models import Poll, PollOption, PollVote, Post, User

MIN_POLL_OPTIONS = 2
MAX_POLL_OPTIONS = 4


def normalize_poll_options(raw_options: list[str]) -> list[str]:
    return [option.strip() for option in raw_options if option.strip()]


def validate_poll_options(options: list[str]) -> None:
    if len(options) < MIN_POLL_OPTIONS or len(options) > MAX_POLL_OPTIONS:
        raise ValueError(
            f"Polls must have between {MIN_POLL_OPTIONS} and {MAX_POLL_OPTIONS} options."
        )


def create_poll_post(author: User, body: str, options: list[str]) -> Post:
    normalized = normalize_poll_options(options)
    validate_poll_options(normalized)

    post = Post(body=body, author=author)
    poll = Poll(post=post)
    for position, text in enumerate(normalized, start=1):
        poll.options.append(PollOption(text=text, position=position))

    db.session.add(post)
    return post


def cast_vote(poll: Poll, user: User, option_id: int) -> PollVote:
    if PollVote.query.filter_by(poll_id=poll.id, user_id=user.id).first():
        raise ValueError("You have already voted on this poll.")

    option = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first()
    if option is None:
        raise ValueError("Invalid poll option.")

    vote = PollVote(poll=poll, option=option, user=user)
    db.session.add(vote)
    return vote


def poll_results(poll: Poll) -> list[dict]:
    options = sorted(poll.options, key=lambda option: option.position)
    counts = dict.fromkeys((option.id for option in options), 0)
    for vote in PollVote.query.filter_by(poll_id=poll.id).all():
        counts[vote.option_id] = counts.get(vote.option_id, 0) + 1

    total_votes = sum(counts.values())
    return [
        {
            "option": option,
            "votes": counts[option.id],
            "percentage": round(counts[option.id] / total_votes * 100, 1) if total_votes else 0.0,
        }
        for option in options
    ]


def user_votes_for_polls(poll_ids: list[int], user_id: int) -> dict[int, int]:
    if not poll_ids:
        return {}

    rows = PollVote.query.filter(
        PollVote.poll_id.in_(poll_ids),
        PollVote.user_id == user_id,
    ).all()
    return {row.poll_id: row.option_id for row in rows}


def poll_template_context(posts: list[Post], user_id: int) -> dict:
    poll_ids = [
        post.display_post.poll.id
        for post in posts
        if post.display_post.poll is not None
    ]
    poll_results_map = {
        post.display_post.id: poll_results(post.display_post.poll)
        for post in posts
        if post.display_post.poll is not None
    }
    return {
        "poll_results": poll_results_map,
        "user_votes": user_votes_for_polls(poll_ids, user_id),
    }
