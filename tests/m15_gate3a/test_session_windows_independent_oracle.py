"""Session and rollover windows, checked against a **hand-written** oracle.

The rule this file exists to obey, and the failure that produced it: the first
R1 dry run built its M1 fixture by importing the very predicate the calendar
used, so the fixture and the calendar agreed **by construction**. Twenty-seven
tests passed over a market-hours boundary that was invented and factually wrong.
A test that compares an implementation to itself cannot falsify it.

So nothing here imports a production predicate to compute an expectation.
Every expected value below is a literal, written by reading the committed text:

* **Ruling 4 FROZEN — sessions.** "Asia 00:00–07:59, Europe 08:00–15:59,
  US 16:00–23:59 UTC".
* **Ruling 4 FROZEN as minimum — rollover.** "the rollover exclusion window is
  **21:55–22:15 UTC minimum** — … may **widen it only for conservatism; it must
  not be narrowed**".
* **prereg §3.7 — clock.** "**UTC** clock; bar timestamp = bucket start. **No DST
  logic (UTC only)**."

The production module is imported only as the **subject** of the assertions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a import session_windows

# ---------------------------------------------------------------------------
# The oracle: literals, read off the committed text by hand
# ---------------------------------------------------------------------------

#: (hour, minute) -> session. Written out, not derived from SESSIONS_UTC.
EXPECTED_SESSION_AT: dict[tuple[int, int], str] = {
    (0, 0): "asia",
    (3, 30): "asia",
    (7, 59): "asia",
    (8, 0): "europe",
    (12, 0): "europe",
    (15, 59): "europe",
    (16, 0): "us",
    (21, 45): "us",
    (23, 59): "us",
}

#: M15 bucket start (hour, minute) -> does it overlap 21:55-22:15?
#: Worked out by hand: a bucket covers [start, start+15).
#:   21:30-21:45 -> ends 21:45, before 21:55            -> no
#:   21:45-22:00 -> contains 21:55..21:59               -> YES
#:   22:00-22:15 -> contained in the window             -> YES
#:   22:15-22:30 -> starts at the window's end          -> no
EXPECTED_ROLLOVER_OVERLAP_AT: dict[tuple[int, int], bool] = {
    (21, 0): False,
    (21, 15): False,
    (21, 30): False,
    (21, 45): True,
    (22, 0): True,
    (22, 15): False,
    (22, 30): False,
    (0, 0): False,
    (12, 0): False,
}

#: Two dates chosen because US DST changes between them: 2025-03-09 is the
#: spring-forward date and 2025-11-02 the fall-back date. prereg §3.7 says "No
#: DST logic (UTC only)", so the answers must be *identical* on both.
DST_TRANSITION_DATES = (
    datetime(2025, 3, 9, tzinfo=UTC).date(),
    datetime(2025, 11, 2, tzinfo=UTC).date(),
    datetime(2025, 3, 30, tzinfo=UTC).date(),  # EU spring forward
    datetime(2025, 10, 26, tzinfo=UTC).date(),  # EU fall back
)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("clock", "expected"), sorted(EXPECTED_SESSION_AT.items()))
def test_session_matches_the_hand_written_oracle(clock: tuple[int, int], expected: str) -> None:
    hour, minute = clock
    moment = datetime(2025, 6, 11, hour, minute, tzinfo=UTC)
    assert session_windows.session_of(moment) == expected


def test_every_minute_of_the_day_lands_in_exactly_one_session() -> None:
    """The partition claim, checked against literal boundaries rather than the map."""
    counts = {"asia": 0, "europe": 0, "us": 0}
    for index in range(24 * 60):
        moment = datetime(2025, 6, 11, index // 60, index % 60, tzinfo=UTC)
        counts[session_windows.session_of(moment)] += 1
    # 00:00-07:59 is 480 minutes; 08:00-15:59 is 480; 16:00-23:59 is 480.
    assert counts == {"asia": 480, "europe": 480, "us": 480}


def test_a_naive_datetime_is_refused() -> None:
    with pytest.raises(session_windows.SessionWindowError, match="naive"):
        session_windows.session_of(datetime(2025, 6, 11, 12, 0))  # noqa: DTZ001


def test_a_non_utc_offset_is_read_in_utc_not_locally() -> None:
    """15:00 at UTC+9 is 06:00Z, which the oracle puts in Asia, not Europe."""
    from datetime import timezone

    tokyo = datetime(2025, 6, 11, 15, 0, tzinfo=timezone(timedelta(hours=9)))
    assert session_windows.session_of(tokyo) == "asia"


# ---------------------------------------------------------------------------
# Rollover
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("clock", "expected"), sorted(EXPECTED_ROLLOVER_OVERLAP_AT.items()))
def test_rollover_overlap_matches_the_hand_written_oracle(
    clock: tuple[int, int], expected: bool
) -> None:
    hour, minute = clock
    moment = datetime(2025, 6, 11, hour, minute, tzinfo=UTC)
    assert session_windows.bucket_overlaps_rollover(moment) is expected


def test_the_rollover_window_is_the_committed_minimum_and_is_not_narrowed() -> None:
    """21:55-22:15, exactly, from the frozen text — and the exclusion is wider."""
    assert session_windows.ROLLOVER_START_MINUTE_OF_DAY == 21 * 60 + 55
    assert session_windows.ROLLOVER_END_MINUTE_OF_DAY == 22 * 60 + 15
    # Two buckets are excluded, not one. A start-only test excludes only 22:00
    # and leaves 21:45 covering 21:55-21:59 -- a narrowing Ruling 4 forbids.
    excluded = [
        (h, m)
        for h in range(24)
        for m in (0, 15, 30, 45)
        if session_windows.bucket_overlaps_rollover(datetime(2025, 6, 11, h, m, tzinfo=UTC))
    ]
    assert excluded == [(21, 45), (22, 0)]


def test_eligibility_is_the_rollover_window_and_nothing_else() -> None:
    """No holiday list exists, so none is applied — and the module says so."""
    assert "FIXED_AT_DESIGN_AUDIT" in session_windows.HOLIDAY_STATUS
    # The stated directions, checked as the *derivation* rather than as strings.
    # An earlier revision asserted "OVERSTATED" for the rate, which a review role
    # showed was self-contradictory: not excluding thin sessions raises modelled
    # cost, which makes the hurdle harder, while leaving those bars in the rate's
    # denominator too. Indeterminate is the honest answer.
    assert "INDETERMINATE" in session_windows.HOLIDAY_CONSEQUENCE
    assert "OVERSTATED" not in session_windows.HOLIDAY_CONSEQUENCE
    assert "DOWN" in session_windows.HOLIDAY_CONSEQUENCE
    # Rollover moves the other way and says so, which is why both are stated.
    assert "LOWERS" in session_windows.ROLLOVER_CONSEQUENCE
    assert "RAISES" in session_windows.ROLLOVER_CONSEQUENCE
    for hour, minute in ((21, 45), (22, 0)):
        assert not session_windows.is_event_eligible_window(
            datetime(2025, 6, 11, hour, minute, tzinfo=UTC)
        )
    for hour, minute in ((0, 0), (12, 0), (21, 30), (22, 15)):
        assert session_windows.is_event_eligible_window(
            datetime(2025, 6, 11, hour, minute, tzinfo=UTC)
        )


# ---------------------------------------------------------------------------
# DST — the property that is actually claimed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("day", DST_TRANSITION_DATES)
def test_the_windows_do_not_move_across_a_dst_transition(day: object) -> None:
    """prereg §3.7: "No DST logic (UTC only)" — so the same UTC clock time
    answers the same on both sides of every transition.

    This is the honest DST test for what this module claims. It does **not**
    assert when the market opens, because no committed source states that and
    D-6 forbids an implementer adding it.
    """
    reference = datetime(2025, 6, 11, tzinfo=UTC)
    for index in range(0, 24 * 60, 5):
        hour, minute = divmod(index, 60)
        on_transition = datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)  # type: ignore[attr-defined]
        control = reference.replace(hour=hour, minute=minute)
        assert session_windows.session_of(on_transition) == session_windows.session_of(control)
        assert session_windows.bucket_overlaps_rollover(
            on_transition
        ) is session_windows.bucket_overlaps_rollover(control)


def test_the_module_reads_no_date_component_at_all() -> None:
    """A market-hours claim needs a **date**; this module may only read a clock.

    The first version of this test was a **name denylist** — it looked for
    `FX_WEEK_OPEN_WEEKDAY`, `in_fx_week` and two others. A review role wrote the
    same Sunday-22:00-to-Friday-22:00 claim back under different names and it
    **passed**. That is the "denylist wearing a structural label" shape this
    repository keeps retiring.

    This is the structural version. Any weekly boundary, any DST rule and any
    holiday list must consult the **date**: a weekday, a calendar date, an
    ordinal or a month. A module that reads only the hour and minute cannot
    express one, whatever it names its constants. So the property asserted is
    the absence of every date accessor, on the AST.
    """
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(session_windows))
    date_accessors = {
        "weekday",
        "isoweekday",
        "date",
        "toordinal",
        "timetuple",
        "tm_wday",
        "tm_yday",
        "tm_mday",
        "tm_mon",
        "tm_year",
        "day",
        "month",
        "year",
        "dst",
        "astimezone",
    }
    reached: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in date_accessors:
            reached.add(node.attr)
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in date_accessors:
                reached.add(name)
    assert not reached, (
        f"the module reads date component(s) {sorted(reached)}. Only the hour and "
        "minute may be read: anything that distinguishes one date from another can "
        "express a market-hours boundary, which D-6 forbids an implementer adding."
    )


def test_the_predicates_are_blind_to_the_date() -> None:
    """The same property, measured rather than read off the AST.

    Every UTC clock time must answer identically on every date it is asked
    about — including a Sunday, a Saturday, a weekday, a leap day and both DST
    transition directions. If any weekly or holiday boundary were present, one
    of these would differ.
    """
    dates = (
        datetime(2025, 5, 4, tzinfo=UTC),  # Sunday
        datetime(2025, 5, 9, tzinfo=UTC),  # Friday
        datetime(2025, 5, 10, tzinfo=UTC),  # Saturday
        datetime(2025, 12, 25, tzinfo=UTC),  # a holiday, if one existed
        datetime(2024, 2, 29, tzinfo=UTC),  # leap day
        datetime(2025, 3, 9, tzinfo=UTC),  # US DST forward
        datetime(2025, 11, 2, tzinfo=UTC),  # US DST back
    )
    for index in range(0, 24 * 60, 5):
        hour, minute = divmod(index, 60)
        answers = {
            (
                session_windows.session_of(day.replace(hour=hour, minute=minute)),
                session_windows.bucket_overlaps_rollover(day.replace(hour=hour, minute=minute)),
            )
            for day in dates
        }
        assert len(answers) == 1, f"{hour:02d}:{minute:02d} answers differently by date"


def test_derivation_containment_imports_nothing_first_party() -> None:
    """The bypass containment must stay stdlib-only, and this is the pin.

    The reader-freedom allowlist calls it "stdlib-only by construction" and an
    earlier revision said "a test below pins that" when no such test existed.
    It exists now. The property matters because `aggregation` imports this
    module, and `aggregation` is reader-free: a first-party import here would
    put whatever it reaches into the aggregator's closure.
    """
    import ast

    from scripts.m15_gate3a import derivation_containment

    tree = ast.parse(Path(derivation_containment.__file__).read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
    assert "scripts" not in modules, f"first-party import in the containment module: {modules}"
    assert "tests" not in modules
