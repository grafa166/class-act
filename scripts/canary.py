"""
Daily live check: does Class Act still actually work?

Everything in tests/ proves the *code* is correct without touching the network.
This proves the *service* is reachable: it builds a real prompt, calls Claude
with a real key, validates the reply, and builds a real Word document -- the
exact path a teacher takes.

It exists because the app was dead for four months and nothing noticed. The
tests would not have caught a revoked key, a retired model, an exhausted
account, or an Anthropic outage. This does.

Deliberately cheap: one small worksheet on the fastest model, a few hundred
output tokens. Well under a penny per run.

Exit codes let the workflow say something useful:
  0  everything works
  2  Anthropic rejected the key            -> the key needs replacing
  3  out of credit                         -> top up
  4  rate limited or Anthropic unavailable -> usually transient
  5  reply was unusable                    -> model or prompt drift
  6  document generation failed            -> a code fault
  1  something else
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anthropic import (  # noqa: E402
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)

from generators.matching import generate_matching_worksheet  # noqa: E402
from llm.client import generate_worksheet_content  # noqa: E402
from llm.prompts import get_prompt  # noqa: E402
from llm.validation import WorksheetContentError, validate_worksheet_content  # noqa: E402

WORKSHEET_TYPE = "matching"


def fail(code, headline, detail=""):
    print(f"::error::{headline}")
    if detail:
        print(detail[:500])
    sys.exit(code)


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No ANTHROPIC_API_KEY configured for this repository — skipping.")
        print("Add one under Settings > Secrets and variables > Actions to enable")
        print("the daily live check.")
        return 0

    print("Building a prompt...")
    prompt = get_prompt(
        WORKSHEET_TYPE,
        year_group="Year 3",
        topic="Vocabulary",
        objective="Pupils can match words to their meanings.",
        age_range="7-8",
        theme_name="Classic",
        theme_icon="books",
        level="expected",
        subject="English",
    )

    print("Calling Claude...")
    try:
        content = generate_worksheet_content(prompt, max_tokens=1500, subject="English")
    except AuthenticationError as exc:
        fail(2, "Anthropic rejected the API key. Class Act cannot generate worksheets.", str(exc))
    except PermissionDeniedError as exc:
        detail = str(exc).lower()
        if "credit" in detail or "billing" in detail:
            fail(3, "Anthropic account is out of credit. Class Act is down.", str(exc))
        fail(2, "The API key lacks permission for this model.", str(exc))
    except BadRequestError as exc:
        if "credit balance" in str(exc).lower():
            fail(3, "Anthropic account is out of credit. Class Act is down.", str(exc))
        fail(5, "Anthropic rejected the request — the API may have changed.", str(exc))
    except RateLimitError as exc:
        fail(4, "Rate limited by Anthropic (usually transient).", str(exc))
    except (APITimeoutError, APIConnectionError) as exc:
        fail(4, "Could not reach Anthropic (usually transient).", str(exc))
    except APIStatusError as exc:
        fail(4, f"Anthropic returned status {exc.status_code}.", str(exc))
    except Exception as exc:  # noqa: BLE001
        fail(1, f"Unexpected failure calling Claude: {type(exc).__name__}", str(exc))

    print(f"  got: {content.get('title', '(untitled)')!r}")

    print("Validating the reply...")
    try:
        validate_worksheet_content(WORKSHEET_TYPE, content)
    except WorksheetContentError as exc:
        fail(5, "Claude's reply was missing fields the worksheet needs.", str(exc))

    print("Building the Word document...")
    try:
        buffer = generate_matching_worksheet(
            content=content,
            theme_key="classic",
            level="expected",
            objective="Pupils can match words to their meanings.",
            extra_spacing=False,
            eal_glossary=False,
            show_answers=False,
        )
        size = len(buffer.getvalue())
    except Exception as exc:  # noqa: BLE001
        fail(6, f"Document generation failed: {type(exc).__name__}", str(exc))

    if size < 5000:
        fail(6, f"Document was suspiciously small ({size} bytes).")

    print(f"  built {size:,} bytes")
    print("\nClass Act is working end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
