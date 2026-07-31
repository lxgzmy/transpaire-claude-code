# Transpire writing style (house voice)

House rules for all writing Claude produces for Transpire — emails, job and
variation summaries, client variation documents, staff alerts, reports. Applied
**on top of** the de-AI patterns in the global `humanizer` skill (which removes AI
tells such as em dashes, rule-of-three padding, and "delve/vibrant/tapestry").

> This is a **v1 default**, grounded in Australian English and the contract-admin
> documents we have seen. It is meant to be tuned. Where a real Transpire writing
> sample is provided, the sample outranks these defaults (see the skill's Voice
> Calibration step). Add samples under the relevant job-role to calibrate.

## Language

- **Australian English** spelling: organise, recognise, colour, labour, licence
  (noun) / license (verb), practise (verb) / practice (noun), metre, catalogue.
- Dates as **DD Month YYYY** or DD/MM/YYYY; metric units; AUD with `$`, and note GST
  where relevant.
- Plain, professional, courteous. Short sentences. Say the thing rather than
  announcing it.

## Register by audience

- **Client / owner-facing** (variation authorities, contract correspondence,
  signature requests): formal, precise, neutral. No marketing language, no emoji,
  no exclamation marks. Match the tone of documents like "Authority for Variation
  To Contract".
- **Internal** (staff alerts, ToDo notes, handover summaries): brief and direct.
  Lead with the action and the job number; one or two sentences is often enough.

## Conventions (from the source manuals — see each role's `rules/`)

- Enforce **UPPERCASE** where the manuals require it (e.g. the `NEW JOB` email
  subject; suburb names in CAPS).
- Reference a job by number + address the way the manuals do, e.g.
  `26049 - LOT 5 (12) PEARSON STREET, GUNNEDAH NSW`.
- **Never invent** client names, addresses, amounts, dates, or job numbers. Missing
  detail is flagged for human input, not guessed.

## Always

- No em dashes or en dashes (humanizer §14).
- No AI tells: no "delve/vibrant/tapestry", no rule-of-three padding, no
  "I hope this helps", no sycophancy, no signposting.
- Every externally visible piece is a **draft for human review** (HITL).

## Job-role voice

Each job-role may add a short voice note under `job-roles/<role>/` (its audience,
typical documents, any role-specific phrasing). The active role's note refines these
defaults.
