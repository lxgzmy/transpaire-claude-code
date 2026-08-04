---
name: transpire-writing
description: >
  Put any Transpire writing into the company's house voice AND strip AI tells before
  it goes to a person or client. Use when drafting or editing emails, job or variation
  summaries, client variation documents, staff alerts, or reports for Transpire.
  Layers the Transpire house style (Australian English, contract-admin register,
  CAPS/naming conventions) on top of the general de-AI humanizer patterns, matched to
  the active job-role and audience.
---

# Transpire writing

Ensure every piece of writing Claude produces for Transpire is (1) free of AI writing
tells and (2) in Transpire's house voice for the right job-role and audience.

## When to use

Drafting or editing any human- or client-facing text for this project: EOI / job
summaries, variation documents and wording, client correspondence, staff alerts,
handover notes, and reports. Skip code, data, and file/link targets.

## Method

1. **De-AI first.** Apply the AI-writing-pattern fixes from the project `humanizer`
   skill (em/en dashes, rule-of-three, "delve/vibrant/tapestry", sycophancy, filler,
   signposting, and the rest). If a real Transpire writing sample is provided,
   calibrate to it — the sample outranks the default style rules (Voice Calibration).
2. **Apply the house style.** Follow `shared/conventions/writing-style.md`: Australian
   English, register by audience, CAPS / naming conventions, and no invented facts.
3. **Match the job-role.** Read the active `job-roles/<role>/` voice note and its
   `rules/`, and fit that role's audience and document type. Contract-admin
   client documents are formal and precise; internal alerts are brief and
   action-first, led by the job number.
4. **Audit and finalise.** Confirm: no AI tells, no em/en dashes, Australian spelling,
   correct register, and no fact / name / number / date / amount that is not in the
   source. Missing detail is flagged for human input, never guessed.

## Output

- Externally visible text is always a **draft for human review**, with its evidence.
- Embedded mode (used as a step inside another task): output only the final text, no
  draft, no audit bullets, no ceremony.

## Reference

- De-AI patterns: the project `humanizer` skill (`.claude/skills/humanizer/`).
- House voice: `shared/conventions/writing-style.md`.
- Role voice and rules: `job-roles/<role>/`.
