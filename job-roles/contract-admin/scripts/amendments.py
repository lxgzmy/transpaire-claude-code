r"""Approved per-job contract amendments (issue #61, CD-10). Stdlib only.

A contract request sometimes asks for a per-job change to the contract and
marks it approved on the same line, for example

    Delete Clause 14. Hidden Site Conditions - Approved by <name>
    Change late payment interest rate from 15% to 12% - Approved

Since 15 Oct 2026 (owner sign-off) the run applies three kinds itself:

  schedule       build contract: a schedule value with a stated old and new
                 value. Only the late-payment interest rate so far (`field:
                 interest_rate`, `from`, `to`): NSW Schedule 1 item 12, the QLD
                 rate on overdue payments.
  strike_clause  build contract, NSW: a whole general-conditions clause named
                 by number (`clause`, optional `title`), struck through -
                 heading, sub-clauses, their numbers and margin notes. Never
                 deleted (the numbering would move), never part of a clause.
  prelim_words   preliminary agreement: words added to or removed from one
                 paragraph of a numbered clause (`clause`), the new paragraph
                 quoted in the request (`expect`). Rewording is refused.

Each amendment carries its request line verbatim (`request_line`). The line
must carry its own approval marker ("Approved", "Approved by <name>") and must
be found word for word in the request text the run saved beside the job JSON
(email*.txt); a prelim_words paragraph must be found there too. Anything else
- a new clause, rewording, a special condition, a line without its own
marker, an approval given somewhere else - stays with a person: the job JSON
lists it under `amendments_for_person` and the report repeats it.

A refused amendment is reported with its reason and the document is saved
with the template wording, as before: a refusal never blocks the save.
"""
import re
from pathlib import Path

KINDS = {"schedule": "build_contract", "strike_clause": "build_contract", "prelim_words": "prelim"}

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"',
           ord(" "): " "}
# the marker closes the line: "... - Approved", "... - approved by <name>."
APPROVAL_RE = re.compile(r"\bapproved(?:\s+by\s+[A-Za-z][\w.' -]*?)?[\s.)\]]*$", re.I)
# ...and is not a request for approval
NEGATION_RE = re.compile(r"\b(?:not|to be|pending|awaiting|subject to|for|needs?|requires?|seeking)"
                         r"\s+(?:be\s+)?approv|\bunapproved\b|approv\w*\s*\?", re.I)


def norm(s):
    """Whitespace collapsed, Word's dashes and curly quotes made plain."""
    s = str(s or "").translate(_DASHES).translate(_QUOTES)
    return re.sub(r"\s+", " ", s).strip()


def request_text(job_path):
    """The request text saved beside the job JSON (email*.txt), normalised; None if none."""
    files = sorted(Path(job_path).resolve().parent.glob("email*.txt"))
    if not files:
        return None
    return norm(" ".join(f.read_text(encoding="utf-8", errors="replace") for f in files))


def check(am, text):
    """(approval marker, "") when the amendment may be applied, else (None, reason)."""
    kind = am.get("kind")
    if kind not in KINDS:
        return None, f"kind {kind!r} is not one the run applies ({', '.join(KINDS)})"
    line = norm(am.get("request_line"))
    if not line:
        return None, "no request_line"
    m = APPROVAL_RE.search(line)
    if not m or NEGATION_RE.search(line):
        return None, "the request line carries no approval marker of its own"
    if text is None:
        return None, "no request text (email*.txt) beside the job JSON to check the line against"
    if line.lower() not in text.lower():
        return None, "the request line is not in the request text word for word"
    if kind == "prelim_words":
        expect = norm(am.get("expect"))
        if not expect:
            return None, "no quoted paragraph (expect)"
        if expect.lower() not in text.lower():
            return None, "the quoted paragraph (expect) is not in the request text word for word"
    return m.group(0).strip(" .)]"), ""


def for_document(values, document, job_path):
    """[(id, amendment, approval or None, reason)] for this document, in job JSON order.

    An amendment of an unknown kind is reported by the document it names, so a
    person sees it refused instead of it vanishing."""
    out, text, loaded = [], None, False
    for n, am in enumerate(values.get("amendments") or [], 1):
        if not isinstance(am, dict):
            continue
        if KINDS.get(am.get("kind"), am.get("document")) != document:
            continue
        if not loaded:
            text, loaded = request_text(job_path), True
        approval, why = check(am, text)
        out.append((str(am.get("id") or f"A{n}"), am, approval, why))
    return out


def for_person(values):
    """The request lines the job JSON leaves with a person, for the report."""
    return [a for a in (values.get("amendments_for_person") or []) if a]
