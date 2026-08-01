# scripts/

Python scripts for the new-job workflow (`../workflows/new-job.md`).

| Script | Status | Does |
|---|---|---|
| `msg_to_text.py` | **Working** | Outlook `.msg` → plain text (headers + body + attachment names). Needs `pip install extract-msg`. |
| `extract_eoi.py` | **Working, tested** | Request-email text → job-data JSON draft sheet per the `JD-*` rules, plus human-attention flags. Handles labelled emails and free-form forwarded chains (subject-line lot/suburb, e-sign client, `$` price, "site a X with a Y façade"). Read-only; touches nothing. |
| `test_extract_eoi.py` | **Passing** | Regression test against `../fixtures/eoi-sample-01.md` / `-expected.md`. Run `python test_extract_eoi.py` after any rule change. |
| `osc_entry.py` | **Skeleton — not runnable live** | pywinauto entry script mirroring manual steps 4–10. Dry-run by default; live mode is blocked until control IDs are captured. |

## Pipeline

```
.msg file ──> msg_to_text.py ──> email.txt
email.txt ──> extract_eoi.py ──> job.json + flags
                                        │  (human reviews sheet, resolves flags,
                                        │   verifies postcode + council by search)
                                        ▼
                                  osc_entry.py --dry-run   (narrates steps)
                                  osc_entry.py --live      (blocked, see below)
```

## Before `--live` can ever run (technical session)

1. On the server with OSC open, capture real control identifiers:
   `inspect.exe` or pywinauto `print_control_identifiers()`; fill the `CTRL`
   map and `OSC_EXE` in `osc_entry.py`.
2. Confirm the approach per `../CLAUDE.md` — OSC write-automation is deferred
   until the technical session with the IT specialist (Adam).
3. Test end-to-end against a **throwaway/test job** in OSC, never a real one.
4. Live mode keeps a HITL gate per screen; the duplicate-search judgment,
   DataBuild email send, and price-mismatch resolution stay human.

## Deliberately not automated

- Lot-number duplicate **judgment** (JD-0.2) — script only reminds.
- Sending the DataBuild email (JD-6.1) — drafted via `transpaire-writing`,
  human sends.
- Price comparison resolution (JD-6.2) — hard stop for a human.
- Phase 2 plan updates — pending the same control-mapping session.
