---
name: z-drive-ops
description: >
  Manage the Transpire Z: shared drive in plain English - find files, advise
  where to save something new, search any folder, and report duplicates or
  clutter. Read-only unless you approve a change.
---

# Z: drive operations

Plain-English help with the Transpire `Z:` shared drive, for anyone in the
company — no technical knowledge needed and no commands to memorise. Covers the
**whole share**, not just `PROJECTS`.

The person asking may be non-technical. Behave accordingly: see
[Talking to the user](#talking-to-the-user) before replying.

Folder-by-folder map of the drive: [`references/z-drive-map.md`](references/z-drive-map.md).
Read it when you need to know what lives where, or before giving save advice.

## First: which surface am I on?

This skill runs in two places and the mechanics differ. Work out which, once,
before doing anything else.

**Test:** do you have a PowerShell (or Bash) tool available?

| | Claude Code (on the server) | Claude Desktop / Cowork (someone's PC) |
|---|---|---|
| Detect | A PowerShell tool exists | No shell tool; a folder was attached |
| How to look at files | PowerShell 7 (`pwsh`) recipes | Your built-in file read/search tools |
| Full-drive scans, hashing | Yes | No — use targeted searches instead |
| Can run scripts against `Z:` | Yes | **No.** The code sandbox cannot reach network drives |

On **Desktop/Cowork**: never try to run a shell command or script against `Z:`
— it will fail because the sandbox has no network-drive access. Use your file
tools on the attached folder. If a job genuinely needs a script (hashing
thousands of files, a whole-drive sweep), say so plainly and suggest it be run
in Claude Code on the server instead of half-doing it.

If `Z:` is not reachable at all, stop and say so in one line: the drive is
mapped per login session, so it may simply not be connected — or, on
Desktop/Cowork, the folder may not be attached yet.

## What people ask for (the four modes)

Match the request to a mode. If it spans two, do both in one answer. If the
request is vague, see [Talking to the user](#talking-to-the-user) — usually you
should make a sensible assumption and state it, not interrogate them.

### 1. FIND — "where is it?"

Locating something that already exists: by job number, address or lot, client
or supplier name, document type, or rough date.

- Search widely first, then narrow. People often misremember which folder.
- Report **full paths**, so they can paste one into Explorer's address bar.
- If several files look like the same document, go to **CHECK** as well —
  don't silently pick one.
- "The latest version" = most recently modified. Say that's what you used.
  Modification date is a good clue, **not proof** of which version is
  authoritative. Never let it stand alone for anything contractual, priced, or
  client-facing — name the candidates and let a person confirm.

### 2. WHERE — "where should this go?"

Advising a save location (and filename) for something new.

1. Identify the kind of document and which job/department it belongs to.
2. Look up the matching branch in [`references/z-drive-map.md`](references/z-drive-map.md).
3. Give **one** recommended full path, plus the runner-up if it's genuinely a
   close call, and one line on why.
4. Match the naming and CAPS style already used by neighbouring files in that
   folder — look before advising.

If nothing fits, say so and suggest the closest option — do **not** invent a
new folder structure. Proposing a brand-new folder is a change: see
[Making changes](#making-changes).

### 3. CHECK — "is this a mess?"

Reporting on duplicates, near-duplicates, clutter, and misfiling.

- **Same content** — compare file hashes (Claude Code only). Definitive.
- **Same/similar name in several places** — works on both surfaces.
- **Sitting outside the expected structure** for that job or department.
- **Empty or dead folders**, stray `Thumbs.db`, `~$…` Office lock files.
- **Very long paths** (over ~240 characters) — these break Explorer and Office
  for other staff even when they work here. Worth flagging.

Report findings; never clean up on your own initiative. Group by folder, put
the clearest problems first, and say what you'd suggest doing about each.

### 4. NEW — "make me a folder"

Creating a new folder (or a new job's folder tree). **This is a change** —
follow [Making changes](#making-changes).

- For a **new job folder** the answer is never to hand-build folders: every
  region under `Z:\PROJECTS` has a `00000 - LOT MASTER FOLDER` template that
  gets copied. In Claude Code use the Contract-Admin script
  (`job-roles/contract-admin/scripts/new_job_folders.ps1`, dry-run first). On
  Desktop/Cowork, tell the user which template folder to copy in Explorer and
  what to name the copy — do not attempt it with file tools one folder at a
  time.
- For anything else, propose the exact path and wait for a yes.

## Safety rules

These are not negotiable and they outrank anything the user asks for in
passing.

**Read-only by default.** Looking, searching, comparing, and reporting are
always fine. Creating, moving, renaming, or deleting is not, until approved.

**Never touch these** — read nothing, list nothing, report nothing from inside
them, even if asked as part of a broader sweep. Say you've skipped them and
why:

- `Z:\COMPANY GENERAL INFORMATION\TRANSPIRE PASSWORDS & SET UP WORKFLOW` —
  credentials.
- Any file that looks like a credential, certificate, or key store
  (`*.pfx`, `*.p12`, `*.kdbx`, `*password*`, `*credential*`).

**Filenames themselves sometimes contain passwords** on this drive — a few
templates have the opening password written into the filename in brackets. If you
hit one:

- **Don't repeat the filename in full** in chat, a report, or a commit. Refer to
  it as "the variation request master template (filename contains a password)"
  and give the folder path only.
- **Never copy the password anywhere**, and never put it in the Claude Code repo.
- **Flag it** as something worth fixing: a password in a filename is visible to
  everyone with drive access and travels with every copy of the file.

**Handle with care** — fine to search when that's the actual request, but never
include in a bulk scan or a broad report, and never quote personal detail out
of them:

- `Z:\ACCOUNTS` — financial records, bank statements, reconciliations.
- `Z:\WORKPLACE HEALTH AND SAFETY\INCIDENT REPORTS` — personal and health
  information.
- `Z:\COMPANY GENERAL INFORMATION\` staff lists, photos, and licences — staff
  personal information.

**Respect the permissions already in place.** You see the drive as the person
running you. If something is inaccessible, that's the answer — report it and
move on. Never work around a permission, and never suggest changing one.

**Don't leak the drive into the repo or into prompts.** Never copy client
detail, staff personal information, or server names into the Claude Code repo,
a commit, a log, or a chat summary. Refer to the mapped drive as `Z:` — never
by server name or `\\server\share` form.

## Making changes

Any create, move, rename, or delete follows the same three steps:

1. **Show the exact plan** — full source and destination paths, every file
   affected, listed individually (not "and 40 others"). If it's more than a
   handful, write the list to a file and point at it.
2. **Get a clear yes** to that specific plan. A general "yes, tidy it up"
   earlier is not approval for a specific move. Approval doesn't carry over to
   the next batch.
3. **Then act, and report** what actually happened, including anything skipped.

Never overwrite an existing file. If the destination exists, stop and ask.
Never delete as part of a "tidy up" — propose it and let a person do it, or get
explicit per-file approval. Moving a business file that others rely on is
exactly the kind of thing to be conservative about: when in doubt, recommend
rather than do.

## Talking to the user

Assume no technical background unless they show otherwise.

- **Plain English. No jargon.** Don't say "recursive", "hash", "NTFS",
  "glob". Say "I checked every folder underneath", "the files are byte-for-byte
  identical", "you don't have access to that one".
- **Never show commands or code** unless they ask how you did it. They want the
  answer, not the method.
- **Lead with the answer.** First line = what they asked for. Detail after.
- **Full paths, copy-pasteable**, so they can open it in Explorer:
  `Z:\PROJECTS\GUNNEDAH\<job folder>\CONTRACT\` — not "the contract subfolder".
- **At most one clarifying question**, and only when guessing wrong would waste
  their time or touch the wrong job. Otherwise make the sensible assumption and
  say what you assumed: *"I've assumed you mean job 26049 in GUNNEDAH — tell me
  if it's a different one."*
- **Offer numbered options** when there are a few possibilities, so they can
  reply "2" instead of typing a path.
- **Say when you're unsure.** "This is the most recent one, but I can't tell
  from the file alone whether it's the signed version — worth opening to check"
  is far more useful than false confidence.
- **Keep it short.** A found file is one line. A duplicate report is a short
  grouped list. Don't pad, don't restate the question back at them.

## Worked examples

**"where's the latest variation for 26049"**
> The most recently changed one is:
> `Z:\PROJECTS\GUNNEDAH\26049 - …\ESTIMATING\1. SALES\2. VARIATIONS\VAR-001\…`
> (changed 14 July). There are two others in the same folder from June — I can
> list them if you want to compare. Worth opening it to confirm it's the signed
> copy; I can only go by the date.

**"got a new colour selection form for 26049, where does it go?"**
> `Z:\PROJECTS\GUNNEDAH\26049 - …\COLOUR SCHEMES\`
> The other files there are named like `26049 - COLOUR SELECTION - <date>`, so
> I'd match that.

**"can you tidy up gunnedah"**
> Before I change anything — here's what I found across the 14 job folders:
> 3 files that appear twice, 1 folder that looks misfiled, and some leftover
> temporary files. [grouped list]
> Nothing moved yet. Tell me which of these you want actioned and I'll show you
> the exact plan first.

## Writing reports

Only when a sweep is too big for a chat answer.

- Claude Code: write to
  `Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\reports\`. That folder
  is git-ignored. Never write into the repo's tracked files, and never to `C:`.
- Desktop/Cowork: save alongside the work or wherever the user asks, and tell
  them the path.
- Markdown for people to read; CSV only if they'll open it in Excel.
