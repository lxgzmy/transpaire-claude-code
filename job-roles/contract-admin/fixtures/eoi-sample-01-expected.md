# Expected output — EOI sample 01

What a correct Phase 1 run of `../workflows/new-job.md` produces from
`eoi-sample-01.md`. Each value cites the JD rule that forces it.
Use to regression-test the future intake skill: same fixture in, this out.

## Step 1 — completeness check

Client ID attached → no request email needed (JD-0.1). Proceed.

## Step 2 — duplicate check reminder

Prompt the human: search OSC for **lot 42, Scenic Rise Estate** before
creating (JD-0.2).

## Step 3 — job-creation draft sheet

| Field | Value | Rule |
|---|---|---|
| Region | `SEQ1` (QLD job) | JD-1.1 |
| Contract No | *Generate Contract No* | JD-1.2 |
| Initial Template | Pre Sales Investor v1 | JD-1.3 |
| New Client | `WEI CHEN` (name as on ID) | JD-1.4 |
| Address 1 | `New Road` (land unregistered) | JD-2.1 |
| Address 2 | `(Scenic Rise Estate)` | JD-2.3 |
| Suburb | `KARANA DOWNS` (CAPS; spelling verified) | JD-2.4 |
| State | `QLD` | JD-2.5 |
| Postcode | `4306` — **verify by web search at run time** | JD-2.6 |
| Job name | `LOT 42.(New Road).KARANA DOWNS 4306` | JD-2.7 |

## Step 5 — job-details draft sheet

| Field | Value | Rule |
|---|---|---|
| Stage | `3` (from email; else `Z:\ESTATES INFORMATION`) | JD-3.1 |
| Design Type | Standard dwelling — **not** Auxiliary (no granny flat) | JD-3.2 |
| Design & Façade | Aspen 24 — Coastal | JD-3.3 |
| Property type | Investment (stated in EOI) | JD-3.4 |
| Private Certifier | Buildable (QLD) | JD-3.6 |
| Local Council | Brisbane City Council — **verify: search `karana downs QLD Local Council`** | JD-3.7 |
| Marketer Company | `SUNRISE PROPERTY MARKETING` | JD-3.9 |
| Marketer Contact | `Jordan BLAKE` | JD-3.9 |
| Marketer Email | jordan@example-marketing.test | JD-3.9 |

## Step 7 — checklist for the human

Activities 1, 2, 6 completed (JD-4); request email attached at JOB and
Item 11, Subject `NEW JOB` (JD-5).

## Step 8 — DataBuild email draft

To the DataBuild administrator; states full project name
`LOT 42.(New Road).KARANA DOWNS 4306` and contract price `$438,750 incl GST`
(JD-6.1). Drafted through `transpire-writing`.

## Step 9 — contact-details sheet

| Field | Value | Rule |
|---|---|---|
| Client address | 12 Sample Street / `CHERMSIDE` / QLD / 4032 — Address 1 only | JD-7.1 |
| Client | WEI CHEN, 0400 000 001, wei.chen@example.test, Primary Comm = Email | JD-7.2 |
| Purchaser slot | Primary (individual purchaser) | JD-7.3 |
| Sales | Priya Nair, Relationship = `SALES` | JD-7.4 |
| Marketer | Jordan Blake, Relationship = `MARKETER_ cc in all emails` | JD-7.5 |
| Primary contact tick | Purchaser (no contrary marketer note) | JD-7.6 |

## Step 10 — price check

Expect DataBuild price `$438,750`; any other value → stop and flag (JD-6.2).

## Open flags the run must raise

1. Land unregistered → address is provisional; await PLAN (JD-2.1, JD-8).
2. Postcode and council values must carry **web-lookup evidence**, not be
   asserted from memory (JD-2.6, JD-3.7).
