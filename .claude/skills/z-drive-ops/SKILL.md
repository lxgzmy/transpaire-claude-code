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

## The top-level folders

18 on the drive, **16 in scope** — `SOFTWARE` and `CLAUDE CODE` are not managed
here. Use this table to pick the top-level folder, then open the map for the
exact subfolder. It saves loading the full map for simple routing, and it is the
one place the out-of-scope, restricted and unreadable folders are listed
together. Verified against the live drive 11 Aug 2026.

| Folder | What's in it, and how to treat it |
|---|---|
| `ACCOUNTS` | Finance: invoicing, payments, receipts, rebates, bank statements, credit applications. **Restricted** — folder names and counts only; never read into the files in a sweep, never quote financial detail. 17 subfolders |
| `ADMINISTRATION` | Day-to-day admin: council forms and fees, insurance, handover, key register, utilities, email templates, socials. 19 subfolders |
| `CLAUDE CODE` | **Out of scope — not managed by this skill.** The automation project, not business records. Don't search, sweep, or advise on it. (Writing a report into its `runtime\shared\reports\` folder is still fine — that's output, not filing advice) |
| `COMPANY GENERAL INFORMATION` | Logo, profile, brochure, licences, staff lists and photos. **Restricted** (staff personal information), and contains the **blocked** passwords folder. 11 subfolders |
| `CONSTRUCTION MANAGER` | Site visits, feedback, fire ants, subcontractor EOIs, and a large uncurated reference library. Treat a hit as someone's reference copy and check `PROCEDURES & FORMS` for the controlled version |
| `DRAFTING` | Archicad, standard details, structural steel, master designs, codes and products. Mostly CAD — see the file-type limits below. Holds an abandoned `ESTATES INFORMATION` stub; ignore it |
| `ESTATES INFORMATION` | **Authoritative** for estates and stages by region, plus driveway regulations by council. NSW 11 estates, SEQ 385, driveway regs for 30 councils |
| `ESTIMATING` | Supplier agreements, subcontractor rates, DataBuild price file, OnSite Companion database, sales and production estimating. **Writable** — earlier "read-only" guidance was wrong. 13 numbered subfolders |
| `IMPORTED` | **Genuinely empty** — 0 files, 0 subfolders, verified rather than inferred from an error |
| `MAINTENANCE` | Defect forms, booking sheets, dilapidation reports, plus a per-address archive |
| `OPERATIONS` | Director and workflow reports, operational guides, supplier agreements, employee records. **Restricted by named account, not by group** — check before answering, because most staff cannot open it at all (see below). Small: 6 subfolders, 22 files |
| `PROCEDURES & FORMS` | The controlled home for **blank** forms and procedures, mirrored by department. Never a completed document. 18 subfolders |
| `PROJECTS` | **All job records**, by region. The only job-shaped folder on the drive. Lifecycle sits at two levels — see FIND |
| `SALES` | Packages by region, marketing agreements, land contracts, finance approvals, floor plan ideas. Loosest structure on the drive; expect more than one search attempt. 31 subfolders |
| `SOFTWARE` | **Out of scope — not managed by this skill.** Don't search, sweep, or advise on it. Send software certificate, licence and manual questions to IT |
| `tony feng test` | Someone's scratch folder at the drive root (11 Aug 2026, one document). **Never a save destination** — flag it as clutter, don't file into it |
| `WORKPLACE HEALTH AND SAFETY` | Audits, SWMS and certificates of currency (49 subcontractor folders), toolbox talks, safety packs. `INCIDENT REPORTS` is **restricted** — personal and health information. 9 subfolders |
| `Z. SUPERSEDED` | Mixed archive. **Never a save destination**; treat a hit as probably superseded |

The split that decides most questions: `PROJECTS` is **job-shaped** (region → job
→ document type); everything else is **department-shaped** (organised by
function). Job number or specific address attached → `PROJECTS`. Otherwise → the
department folder.

Folder-by-folder map of the drive: [`references/z-drive-map.md`](references/z-drive-map.md).
**Read it before answering any "where is it" or "where does this go" question**
that the table above doesn't settle outright. It opens with a router — an A–Z
index of about seventy things people ask for, three questions that pick the
top-level folder, and a table of the documents that legitimately live in more
than one place. Use that router rather than reasoning from folder names; the
folder names alone will not tell you whether something belongs with a job, with
a department, or with the blank forms.

## What this skill can and cannot see

Be straight about this rather than implying a search was exhaustive.

- **It searches names and locations, not the inside of documents.** Filenames,
  folder paths and modification dates — not the text within a contract or
  spreadsheet. "Find the variation that mentions the retaining wall" is not a
  question it can answer by searching; "find the variations for job 24025" is.
  It can open a specific file it has found, if asked and if the format allows.
- **Many files can't be opened at all.** Job folders and safety folders are
  mostly PDFs and Office documents and read fine. `DRAFTING` is mostly Archicad
  and CAD (`.pln`, `.gsm`, `.dwg` and similar) — about 46% of files there cannot
  be opened, only located by name. Outlook `.msg` files and legacy `.doc` are
  also name-only.
- **A scan is always scoped to one branch, and slow.** Listing a single region
  recursively takes seconds to minutes; drive-wide enumeration extrapolates to
  the better part of ten minutes before anything is read. Say which branch you
  checked and offer the next one.

## First: which surface am I on?

This skill runs in two places and the mechanics differ. Work out which, once,
before doing anything else.

**Test:** do you have a PowerShell (or Bash) tool available?

| | Claude Code (on the server) | Claude Desktop / Cowork (someone's PC) |
|---|---|---|
| Detect | A PowerShell tool exists | No shell tool; a folder was attached |
| How to look at files | PowerShell 7 (`pwsh`) recipes | Your built-in file read/search tools |
| Scans and hashing | Yes, **scoped to a named branch** | No — use targeted searches instead |
| Can run scripts against `Z:` | Yes | **No.** The code sandbox cannot reach network drives |

**There is no such thing as a whole-drive sweep.** The share is roughly 1,700 GB;
a single region takes minutes just to list, and hashing everything is not
achievable in a conversation. Always scope a scan to a named branch, say in your
answer which branch you scoped it to, and offer to do a neighbouring branch next.
If someone genuinely needs the whole drive compared, that's a scheduled job to
raise with IT, not a chat answer. Never let a scoped scan be reported as if it
covered everything.

On the Claude Code surface, the PowerShell techniques — checking the drive is
mapped, literal-path handling, inventory and hashing recipes, creating an output
folder — live in the **`windows-fileops`** skill. Use it for the *how*; this
skill stays the *what* and *whether*.

On **Desktop/Cowork**: never try to run a shell command or script against `Z:`
— it will fail because the sandbox has no network-drive access. Use your file
tools on the attached folder. If a job genuinely needs a script (hashing
thousands of files, a large sweep), say so plainly and suggest it be run
in Claude Code on the server instead of half-doing it.

Also on Desktop/Cowork: **you only see what was attached.** Staff are told to
attach `Z:\PROJECTS`, which covers job work but none of the department folders.
If a request needs `ADMINISTRATION`, `PROCEDURES & FORMS`, `WORKPLACE HEALTH AND
SAFETY` or similar and you can't see it, say so in one line and tell them to
attach `Z:\` instead — don't answer from the map alone as though you had checked.

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
- **Looking for a job? Lifecycle folders exist at two levels, and most job
  folders are in them.** Search in this order and don't stop early:
  1. the region folder (`Z:\PROJECTS\<region>\`)
  2. that region's own lifecycle subfolders — `HANDED OVER`,
     `ARCHIVE-HANDED OVER`, `CANCELLED`
  3. the top-level `Z:\PROJECTS\COMPLETED CONTRACTS\` and `CANCELLED CONTRACTS\`

  730 job folders sit at step 2 and 431 at step 3, against 329 in the live
  region folders — so **about 78% of jobs are not where a region-level look
  would find them**. Only after all three may you say a job doesn't exist.
- **Match a job number on its first five digits, not on `"26049 - "`.** Real
  folder names vary around the dash (`26003- LOT`, `16001 -LOT`, double spaces),
  so an exact-prefix match misses genuine jobs.
- **On the Claude Code surface, don't hand-write this search** — run
  [`scripts/find_job.ps1`](scripts/find_job.ps1) (`pwsh find_job.ps1 26049`, or
  words like `"lot 13 zhang"`, optional `-Region`). It covers all three levels
  above, applies the five-digit rule, marks cancelled hits, and answers in about
  two seconds. Desktop/Cowork without a shell still searches with file tools.
- "The latest version" = most recently modified. Say that's what you used.
  Modification date is a good clue, **not proof** of which version is
  authoritative. Never let it stand alone for anything contractual, priced, or
  client-facing — name the candidates and let a person confirm.

### 2. WHERE — "where should this go?"

Advising a save location (and filename) for something new.

**Use the router in the map — don't reason from folder names.** Open
[`references/z-drive-map.md`](references/z-drive-map.md) and work in this order:

1. **A–Z index** — look up the words they used ("Form 2", "cert of currency",
   "put and call"). Most requests are answered outright here.
2. **Three questions that pick the folder** — if the index doesn't cover it:
   is a job number attached? is it blank or filled in? is it the controlled copy
   or someone's working copy?
3. **Same document, different homes** — check whether this document type has
   more than one legitimate home. Variations, contracts, colour schemes, SWMS,
   safety packs, QA forms, defects forms, insurance certificates, BASIX and
   quotes all do. **This is the one case where asking is better than guessing.**
4. **Per-folder section** — for the exact subfolder.

Then:

- Give **one** recommended full path, plus the runner-up if it's genuinely a
  close call, and one line on why.
- Match the naming and CAPS style already used by neighbouring files in that
  folder — look before advising.
- **Blank form vs completed document** is the most common way to get this wrong.
  A blank template belongs in `PROCEDURES & FORMS`; the filled-in one belongs
  with its job or its department. If their wording doesn't make clear which they
  have, ask.

If nothing fits, say so and suggest the closest option — do **not** invent a
new folder structure. Proposing a brand-new folder is a change: see
[Making changes](#making-changes).

### 3. CHECK — "is this a mess?"

Reporting on duplicates, near-duplicates, clutter, and misfiling.

**Scope first.** Agree a branch — one job, one region, one department folder —
before you start, and name it in the answer. A request to "check the whole drive"
becomes "I've checked GUNNEDAH; want me to do SYDNEY next?".

- **Same content** — compare file hashes (Claude Code only, within the scoped
  branch). Definitive.
- **Same/similar name in several places** — works on both surfaces.
- **Sitting outside the expected structure** for that job or department.
- **Files dumped at a folder's root** instead of in a subfolder. This is the most
  widespread problem on the drive — some department folders have 60–80 loose files
  at the top — and usually the most useful thing you can report.
- **Empty or dead folders**, and leftover junk: `Thumbs.db`, `desktop.ini`, `~$…`
  Office lock files, `.lnk` shortcuts, files with no extension.
- **Very long paths** (over ~240 characters) — these break Explorer and Office
  for other staff even when they work here. Worth flagging.

Filter the junk *out* of reports rather than listing it, and never report a
folder as empty when you simply couldn't read it — "you don't have access to that
one" is a different and more useful answer.

Report findings; never clean up on your own initiative. Group by folder, put
the clearest problems first, and say what you'd suggest doing about each.

### 4. NEW — "make me a folder"

Creating a new folder (or a new job's folder tree). **This is a change** —
follow [Making changes](#making-changes).

**The answer is almost never to hand-build folders.** The drive has three
templates, and the right move is to copy the matching one:

| Creating | Copy |
|---|---|
| A new job | `Z:\PROJECTS\<region>\00000 - LOT MASTER FOLDER` |
| A new sales package | `Z:\SALES\MASTER FOLDER TEMPLATE\LOT` |
| A new estate | `Z:\ESTATES INFORMATION\<NSW\|SEQ>\000 A MASTER_ESTATE_FOLDER (do not change)` |

- For a **new job folder** in Claude Code, use the Contract-Admin script
  (`job-roles/contract-admin/scripts/new_job_folders.ps1`, dry-run first). On
  Desktop/Cowork, tell the user which template folder to copy in Explorer and
  what to name the copy — do not attempt it with file tools one folder at a
  time.
- Before creating a job folder, check the number isn't already used anywhere —
  including the lifecycle folders listed under **FIND**. A number reused from a
  completed or cancelled job is a duplicate, not a new job.
- For anything else, propose the exact path and wait for a yes.

## Safety rules

These are not negotiable and they outrank anything the user asks for in
passing.

**Read-only by default.** Looking, searching, comparing, and reporting are
always fine. Creating, moving, renaming, or deleting is not, until approved.

**Out of scope — `Z:\SOFTWARE` and `Z:\CLAUDE CODE`.** Transpire does not manage
these through this skill. Don't search them, don't include them in sweeps,
counts or clutter reports, and don't give save advice for them. Treat them as if
they weren't on the drive; if a request lands on one, say it's outside what this
skill covers — software certificates, licences and manuals go to IT, and
`CLAUDE CODE` is the automation project rather than business records.

Two carve-outs, both about output rather than filing advice: writing a report
into `Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\reports\` is still
correct (see [Writing reports](#writing-reports)), and this is a **scope**
decision, not a permission one — the credential rules below still apply
everywhere on the drive, these two folders included.

**Never touch these** — read nothing, list nothing, report nothing from inside
them, even if asked as part of a broader sweep. Say you've skipped them and
why:

- `Z:\COMPANY GENERAL INFORMATION\TRANSPIRE PASSWORDS & SET UP WORKFLOW` —
  credentials.
- Any file that looks like a credential, certificate, or key store, **anywhere
  on the drive**: `*.pfx`, `*.p12`, `*.kdbx`, `*.cer`, `*.crt`, `*.pem`,
  `*.key`, `*.jks`, `*.ppk`, `*.asc`, `*.env`, `*.rdp`, `*password*`,
  `*credential*`, `*secret*`. Real key and certificate files exist on this
  drive, so this is not hypothetical — `Z:\OPERATIONS` holds a plain-text
  DataBuild credentials file at its top level. **All** of these patterns, the
  name-based ones included, are blocked in `.claude/settings.json`, so a read is
  refused by the tool layer rather than relying on you to remember. Matching is
  case-insensitive and covers the whole path, and the `Edit(...)` variants also
  stop a shell command from moving or deleting one. Verified by probe file
  10 Aug 2026; an earlier note here claimed name patterns could not be enforced
  this way, and that was wrong.
- Contacts exports: `*.vcf`. `Z:\OPERATIONS` holds phone-contact backups —
  bulk personal data with no reason to be opened. Blocked at the tool layer too.

**Filenames themselves sometimes contain passwords** on this drive — a template
has the opening password written into the filename in brackets. If you hit one:

- **Don't repeat the filename in full** in chat, a report, or a commit. Refer to
  it as "the variation-request template sitting in the CUSTOMER SELECTIONS
  folder (filename contains a password)" and give the folder path only — it's a
  Request for Variation master template, not a colour or customer-selection
  form, apparently misfiled — it sits under
  `ESTIMATING\1. SALES\4. CUSTOMER SELECTIONS` in the job template, and a copy is
  in every job folder built from the template.
- **Never copy the password anywhere**, and never put it in the Claude Code repo.
- **Flag it** as something worth fixing: a password in a filename is visible to
  everyone with drive access and travels with every copy of the file.

**Handle with care** — fine to search when that's the actual request, and fine to
count folders when mapping the drive's structure, but **never** read into the
files as part of a broad sweep, and never quote personal or financial detail out
of them:

- `Z:\ACCOUNTS` — financial records, bank statements, reconciliations.
- `Z:\WORKPLACE HEALTH AND SAFETY\INCIDENT REPORTS` — personal and health
  information.
- `Z:\COMPANY GENERAL INFORMATION\` staff lists, photos, and licences — staff
  personal information.
- `Z:\OPERATIONS` — director-level reporting and employee records. Also the one
  folder deliberately walled off from general staff (see below).

The line: folder names and counts, yes — that's how the drive gets mapped.
Filenames, contents, or anything identifying a person, no.

**Respect the permissions already in place.** You see the drive as the person
running you. If something is inaccessible, that's the answer — report it and
move on. Never work around a permission, and never suggest changing one.

**`Z:\OPERATIONS` is restricted to named accounts.** It is the only top-level
folder with inherited permissions switched off, and the company-wide `Z:` drive
group is deliberately not on its access list — seven named accounts are, mostly
directors and administrators. So whether you can read it depends entirely on who
is running you, and for most staff the answer is no.

Two consequences. First, **try it, don't predict it**: attempt the listing and
report what actually came back, rather than assuming access either way. Second,
if the read fails, say the folder is restricted to specific people and suggest
asking a director or IT — do **not** describe what is in it. The structure
recorded in the map exists so the skill can route a question, not so it can be
recited to someone the permissions were designed to exclude.

**Never report "empty" when you mean "couldn't read".** If a folder errors, say
you don't have access to it. `Z:\OPERATIONS` was mistakenly recorded as empty for
exactly this reason, and the map then suggested deleting it. An unreadable folder
is never a removal candidate.

**Don't leak the drive into the repo or into prompts.** Never copy client
detail, staff personal information, or server names into the Claude Code repo,
a commit, a log, or a chat summary. Refer to the mapped drive as `Z:` — never
by server name or `\\server\share` form.

This includes **server names hidden inside filenames**: drive-shortcut files at
the `Z:\` root and in several department folders have the file server's name in
them. Filter those files out of any listing or report rather than repeating their
names.

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
  `Z:\PROJECTS\GUNNEDAH\<job folder>\CONTRACT\`, or
  `Z:\WORKPLACE HEALTH AND SAFETY\SWMS and Certs of Currency\` — not "the
  contract subfolder" or "the safety folder".
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

**"where's the latest variation for 24025"**
> The most recently changed one is:
> `Z:\PROJECTS\GUNNEDAH\24025 - …\ESTIMATING\1. SALES\2. VARIATIONS\VAR-026\…`
> (changed 2 March, alongside a matching confirmation email from the same day).
> There are 25 earlier variations in the same folder going back to June 2025 — I
> can list them if you want to compare. Worth opening it to confirm it's the
> signed copy; I can only go by the date.

**"got a new colour selection form for 24025, where does it go?"**
> `Z:\PROJECTS\GUNNEDAH\24025 - …\COLOUR SCHEMES\`
> The other files there are named like `EXTERNAL COLOURS - <scheme name>` or
> `INTERNAL COLOUR - <scheme name>` — no job number or date in the filename — so
> I'd match that style rather than assume.

**"where do I put a new subbie's SWMS?"**
> `Z:\WORKPLACE HEALTH AND SAFETY\SWMS and Certs of Currency\`
> There's a folder per subcontractor in there (49 of them), so make one in their
> name if they're new. Their certificate of currency goes in the same folder.

**"can you tidy up gunnedah"**
> Before I change anything — here's what I found across the 13 job folders in
> GUNNEDAH (I haven't looked at the other regions):
> 3 files that appear twice, 1 folder that looks misfiled, and some leftover
> temporary files. [grouped list]
> Nothing moved yet. Tell me which of these you want actioned and I'll show you
> the exact plan first. Want me to do SYDNEY next?

**"is job 25xxx anywhere? I can't find it"**
> Found it — it's been handed over, so it's moved out of the live region folder:
> `Z:\PROJECTS\SYDNEY\HANDED OVER\25xxx - …`
> That's where finished Sydney jobs go. SEQ uses `ARCHIVE-HANDED OVER`, and some
> older jobs sit in `Z:\PROJECTS\COMPLETED CONTRACTS` instead.

## Writing reports

Only when a scoped sweep is too big for a chat answer.

- Claude Code: write to
  `Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\reports\`. That folder is
  git-ignored, and it may not exist yet — create it if it's missing (see
  `windows-fileops` for the command). Never write into the repo's tracked files,
  and never to `C:`.
- Desktop/Cowork: save alongside the work or wherever the user asks, and tell
  them the path.
- Markdown for people to read; CSV only if they'll open it in Excel.
