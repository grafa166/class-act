"""
Who may use this app, and how much they may use it.

Every worksheet costs the account holder money, so a hosted copy needs two
things the local copy does not: a door, and a ceiling.

  * A shared password, set by the owner. Without the password nobody gets in.
  * A daily cap on worksheets, so a link passed around a staffroom -- or a
    stuck browser tab -- cannot quietly drain the account.

Both are configured by the owner and by nobody else. If no password is set the
app runs open, so running it on your own machine stays a double-click.
"""

import datetime as _datetime
import hmac
import os

import streamlit as st

# Config comes from Streamlit secrets when hosted, or the environment locally.
PASSWORD_SETTING = "APP_PASSWORD"
DAILY_LIMIT_SETTING = "DAILY_WORKSHEET_LIMIT"
DEFAULT_DAILY_LIMIT = 100


def _setting(name, default=None):
    """Read a setting from Streamlit secrets, falling back to the environment."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # noqa: BLE001 - no secrets file at all is normal locally
        pass
    return os.getenv(name, default)


# --------------------------------------------------------------------------
# The door
# --------------------------------------------------------------------------


def password_is_configured():
    return bool(_setting(PASSWORD_SETTING))


def check_password():
    """Show a password gate. Returns True once the visitor is through it.

    Returns True immediately when no password is configured, so the local
    copy is unaffected.
    """
    if not password_is_configured():
        return True

    if st.session_state.get("_access_granted"):
        return True

    st.markdown("### 🔒 Class Act")
    st.write("This tool is password protected. Please enter the password to continue.")

    entered = st.text_input("Password", type="password", key="_access_password")

    if entered:
        # hmac.compare_digest avoids leaking the answer through response timing.
        if hmac.compare_digest(str(entered), str(_setting(PASSWORD_SETTING))):
            st.session_state["_access_granted"] = True
            st.rerun()
        else:
            st.error("That password is not correct.")

    st.caption("If you need access, ask whoever shared this link with you.")
    return False


# --------------------------------------------------------------------------
# The ceiling
# --------------------------------------------------------------------------


@st.cache_resource
def _usage_counter():
    """Worksheet tally shared by everyone using this copy of the app.

    Held in memory, so it resets if the host restarts the app. That is fine:
    this is a guard rail against runaway cost, not an accounting record.
    """
    return {"date": None, "count": 0}


def daily_limit():
    try:
        return int(_setting(DAILY_LIMIT_SETTING, DEFAULT_DAILY_LIMIT))
    except (TypeError, ValueError):
        return DEFAULT_DAILY_LIMIT


def _today():
    return _datetime.date.today().isoformat()


def worksheets_used_today():
    counter = _usage_counter()
    if counter["date"] != _today():
        counter["date"] = _today()
        counter["count"] = 0
    return counter["count"]


def worksheets_remaining_today():
    return max(0, daily_limit() - worksheets_used_today())


def record_worksheets(count=1):
    counter = _usage_counter()
    if counter["date"] != _today():
        counter["date"] = _today()
        counter["count"] = 0
    counter["count"] += count
    return counter["count"]


def check_daily_limit(requested=1):
    """Stop generation if today's allowance is spent.

    Returns True to proceed. Renders its own explanation and returns False
    when the cap is reached.
    """
    remaining = worksheets_remaining_today()
    if remaining <= 0:
        st.error(
            f"This tool has reached its daily limit of {daily_limit()} worksheets."
        )
        st.info("The allowance resets tomorrow. Contact the owner if you need more.")
        return False

    if requested > remaining:
        st.warning(
            f"Only {remaining} worksheet{'s' if remaining != 1 else ''} left in "
            "today's allowance — generating what's left."
        )
    return True
