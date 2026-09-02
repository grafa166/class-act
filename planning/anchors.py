"""Where a lesson comes from, per subject.

The anchor is asked for *before* anything is written, because the honest answer
differs by subject and getting it wrong for maths is the one failure here that
could harm a child's learning rather than merely waste the teacher's time.

At St Anthony's:

  * **Maths follows White Rose**, which the school mandates. Its sequence,
    methods and vocabulary are part of the scheme and are tied to the school's
    calculation policy. A plausible alternative progression invented alongside
    it would put prerequisites out of order and contradict what the rest of the
    school teaches. So maths is LOCKED: the small step *is* the objective, and
    nothing here may re-sequence it.

  * **Everything else is hers to build.** Boost covers science, history,
    geography and computing, and its long- and medium-term plans have to be
    followed -- but they are, in her words, old and bad. Lighting the Path
    frames RE. English runs off the school's own medium-term plan and the RAP
    text of the half-term. In each case the scheme is a reference point, not a
    script: its coverage and order are kept, its teaching is rebuilt.

One rule spans all of them: **publisher content is never reproduced.** White
Rose, Boost and Lighting the Path are all copyrighted. The teacher supplies the
step, objective or unit she is working from; this app supplies the teaching
around it.
"""

from dataclasses import dataclass

# An anchor is either mandated by the school, or the teacher's to build.
LOCKED = "locked"
OWN_BUILD = "own_build"


@dataclass(frozen=True)
class Anchor:
    """How planning for one subject is constrained."""

    subject: str
    mode: str
    scheme: str | None
    note: str

    @property
    def may_resequence(self):
        """Whether the order of teaching may be changed.

        False for a mandated scheme. This is the flag that stops the planner
        inventing a maths progression alongside White Rose.
        """
        return self.mode != LOCKED

    @property
    def teacher_supplies_content(self):
        """True wherever a named publisher scheme is involved.

        The copyright boundary: she pastes, uploads or photographs the page she
        is working from. We never ship the publisher's material.
        """
        return self.scheme is not None


_BOOST = (
    "Boost's coverage and order are kept -- she is accountable for those. The "
    "teaching is rebuilt, because that is where the scheme is thin."
)

ANCHORS = {
    "Maths": Anchor(
        subject="Maths",
        mode=LOCKED,
        scheme="White Rose",
        note=(
            "School-mandated. The small step is the objective, word for word. "
            "Never re-sequenced -- that would fight the calculation policy."
        ),
    ),
    "Science": Anchor("Science", OWN_BUILD, "Boost", _BOOST),
    "History": Anchor("History", OWN_BUILD, "Boost", _BOOST),
    "Geography": Anchor("Geography", OWN_BUILD, "Boost", _BOOST),
    "Computing": Anchor("Computing", OWN_BUILD, "Boost", _BOOST),
    "RE": Anchor(
        subject="RE",
        mode=OWN_BUILD,
        scheme="Lighting the Path",
        note=(
            "Oxford's programme delivering the Religious Education Directory. "
            "Its branch and unit frame the lessons; she builds them."
        ),
    ),
    "English": Anchor(
        subject="English",
        mode=OWN_BUILD,
        scheme=None,
        note=(
            "The school's own medium-term plan, plus this half-term's RAP text. "
            "No published scheme to work around."
        ),
    ),
    "Languages": Anchor(
        subject="Languages",
        mode=OWN_BUILD,
        scheme=None,
        note="No published scheme recorded.",
    ),
}


def anchor_for(subject):
    """The anchor for a subject.

    An unrecognised subject defaults to OWN_BUILD rather than LOCKED. Failing
    to 'locked' would block correct work on a subject we simply have no record
    of; failing to 'build' only means the teacher is offered more freedom than
    she may want, which she can see and ignore.
    """
    return ANCHORS.get(
        subject,
        Anchor(
            subject=subject,
            mode=OWN_BUILD,
            scheme=None,
            note="No scheme recorded for this subject.",
        ),
    )


def is_locked(subject):
    """True if the school mandates this subject's sequence."""
    return anchor_for(subject).mode == LOCKED


def suggest_lesson_count(weeks, objectives):
    """How many lessons a unit should probably run to.

    Six is a suggestion, not a rule -- the right number depends on the topic and
    how much term is left, and the teacher overrides it. Two constraints shape
    the suggestion: one lesson per remaining week is the realistic ceiling for a
    foundation subject, and every objective still has to be covered, so coverage
    wins over the calendar when they disagree.
    """
    by_calendar = max(1, int(weeks))
    return max(by_calendar, int(objectives), 1)
