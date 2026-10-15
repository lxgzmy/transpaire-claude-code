"""Unit test for amendments.py - which request lines count as approved (CD-10, issue #61).

    python test_amendments.py

Synthetic lines only. A line counts when it closes with its own approval
marker, does not ask for approval, and is found word for word in the saved
request text; Word's dashes and quotes do not matter.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import amendments as am  # noqa: E402

REQUEST = am.norm("""Item 3. Delete Clause 14. Hidden Site Conditions – Approved by Test
Item 4. Change late payment interest rate from 15% to 12% - Approved
Item 6. Change the building period to 300 days - to be approved
Item 7. Add the new special condition (approved?)
Item 8. Change the deposit - Approval pending
Item 9. Delete clause 20 - not approved
Item 10. Update clause 4 as below - approved by Test.
The Party shall not disparage the other Party with words.
""")

CASES = [
    ({"kind": "strike_clause", "request_line": "Item 3. Delete Clause 14. Hidden Site Conditions - Approved by Test"},
     "Approved by Test"),
    ({"kind": "schedule", "request_line": "Item 4. Change late payment interest rate from 15% to 12% - Approved "},
     "Approved"),
    ({"kind": "schedule", "request_line": "Item 6. Change the building period to 300 days - to be approved"}, None),
    ({"kind": "strike_clause", "request_line": "Item 7. Add the new special condition (approved?)"}, None),
    ({"kind": "schedule", "request_line": "Item 8. Change the deposit - Approval pending"}, None),
    ({"kind": "strike_clause", "request_line": "Item 9. Delete clause 20 - not approved"}, None),
    ({"kind": "strike_clause", "request_line": "Item 11. Delete clause 21 - Approved"}, None),          # not in the text
    ({"kind": "new_clause", "request_line": "Item 4. Change late payment interest rate from 15% to 12% - Approved"},
     None),                                                                                            # kind not allowed
    ({"kind": "prelim_words", "request_line": "Item 10. Update clause 4 as below - approved by Test.",
      "expect": "The Party shall not disparage the other Party with words."}, "approved by Test"),
    ({"kind": "prelim_words", "request_line": "Item 10. Update clause 4 as below - approved by Test.",
      "expect": "The Party shall not disparage anyone."}, None),                                     # paragraph not quoted
]


def main():
    fails = 0
    for amend, want in CASES:
        got, why = am.check(amend, REQUEST)
        ok = (got == want) if want else (got is None and why)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {amend['request_line'][:60]!r} -> {got or 'refused: ' + why}")
    got, why = am.check(CASES[0][0], None)
    ok = got is None and "no request text" in why
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  no request text beside the job JSON -> refused")
    print("\nPASS" if not fails else f"\nFAIL - {fails} case(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
