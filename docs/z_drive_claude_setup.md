# Z: drive help with Claude — setup & reference

Setting up and maintaining `Z:` drive help. **For IT / whoever rolls this out.**

The skill behind it: [`.claude/skills/z-drive-ops/`](../.claude/skills/z-drive-ops/SKILL.md).

> **Looking for the staff-facing guide?** That's the shorter, formatted version:
> [`Transpire_z_drive_claude_guide.pdf`](Transpire_z_drive_claude_guide.pdf) in
> this folder (source: [`z_drive_claude_guide.html`](z_drive_claude_guide.html)).
> A copy is also kept at `Z:\CLAUDE CODE\cowork-projects\2.z_drive\` for handing
> to end users. Hand out the PDF, not this file.

**What it does, in one line:** you ask "where's the latest variation for
24025?" or "where should this colour selection go?" and it answers with a path
you can paste into Explorer.

## How staff use it: Claude Desktop, Code mode

There is one supported way to reach it, and there is nothing to package or
distribute:

1. Open **Claude Desktop** and sign in with your own account.
2. Switch to **Code** mode.
3. Pick the project folder **`transpire-claude-code`** — the checkout at
   `Z:\CLAUDE CODE\transpire-claude-code`. If Code mode is pointed at a different
   folder, switch it: skills only load from this repo's `.claude/skills/`.
4. Accept the folder-trust prompt. Once only, per user.
5. Run:
   ```
   /z-drive-ops where should a signed variation for 24025 go?
   ```
   or just describe what you want in plain English — the skill also activates on
   its own when a request is clearly about the drive.

Steps 1–4 are a one-off; day to day it's just step 5.

Code mode **is** Claude Code — full shell access, the mapped `Z:` drive, every
skill in the repo — just reached through the desktop app instead of a terminal.
There's nothing to package, upload, or enable per person, and no folder to
attach: the repo (and the `Z:` drive it can see) is the same for whoever opens
it, so the advice is consistent for everyone. Power users who prefer a terminal
can run the `claude` CLI from the same checkout instead — same skill, same drive,
same slash command, just a different way in.

**The one thing that must be right:** `Z:` is a network share mapped per login
session, so the machine running the Code-mode session needs `Z:` mapped and
connected. If a session says it can't see `Z:` or a folder inside it "doesn't
exist" when you know it does, check that first — it is nearly always a mapping
problem, not a Claude problem.

## First-time walkthrough

Five things to try, in order, and what to notice about each. Tested 10 Aug 2026
against job **24025** in GUNNEDAH (`LOT 12 YARRAANDOO CLOSE`), which — unlike
some newer jobs — actually has variation and colour-scheme files in it, so the
walkthrough shows real behaviour rather than an empty folder.

1. **Find something** — *"where's the latest variation for job 24025?"*
   It gives a full path (`…\ESTIMATING\1. SALES\2. VARIATIONS\VAR-026\…`), says
   which date it went by, and points out that the date doesn't prove it's the
   signed copy.
2. **Ask where something goes** — *"I've got a new colour selection form for
   24025, where should I save it?"* It recommends `…\COLOUR SCHEMES\` **and**
   matches the naming style already used there (e.g. `EXTERNAL COLOURS -
   <scheme name>`, no job number or date in the filename — check what's actually
   in the folder rather than assuming).
3. **Ask for a tidy check** — *"any duplicates in the GUNNEDAH jobs?"*
   It reports what it found and changes nothing.
4. **Ask it to act** — *"just delete the duplicates for me"*
   It shows the exact list and asks first. This is the important one: it never
   quietly moves or deletes anyone's files.
5. **Try a blocked folder** — ask for something in
   `Z:\COMPANY GENERAL INFORMATION\TRANSPIRE PASSWORDS & SET UP WORKFLOW`.
   It refuses and explains why. (Verified: the permission rules in
   `.claude/settings.json` block this at the tool level, not just by the skill
   choosing to refuse — trying it directly returns a permission error.)

If you're walking someone else through this with a different job number, check
it first — plenty of newer jobs genuinely have nothing in `VARIATIONS` or
`COLOUR SCHEMES` yet, which is a fine but less illustrative answer.

## Limits, stated plainly

- **`Z:` has to be mapped and connected on the machine running the session.**
  Code mode reaches `Z:` the same way any other program on that machine does — if
  the drive isn't mapped there, Claude can't see it either, and will say so
  rather than guess.
- **Two folders are deliberately out of scope:** `Z:\SOFTWARE` (software
  certificates, licences, manuals — send these to IT) and `Z:\CLAUDE CODE` (the
  automation project, not business records). The skill doesn't search, sweep or
  advise on either. Writing a report into
  `Z:\CLAUDE CODE\transpire-claude-code\runtime\shared\reports\` is still its
  normal output path — that's a carve-out, not a contradiction.
- **It searches names and locations, not the contents of documents.** Filenames,
  folder paths and dates. "Find the variations for job 24025" works; "find the
  variation that mentions the retaining wall" does not. It can open a specific
  file it has already found, if asked and if the format allows.
- **A large share of files cannot be opened at all, only located by name.**
  Measured across a 31,320-file sample: job folders are 56% readable formats
  (PDF/Office) and safety 86%, but `DRAFTING` is 46% Archicad and CAD
  (`.pln`, `.gsm`, `.dwg`) and only 17% readable. Outlook `.msg` and legacy
  `.doc` are name-only too. This is a property of the file formats, not a
  configuration problem.
- **There are no whole-drive sweeps.** The share is about 1,700 GB. Scans are
  scoped to one branch: a job, a region, or a department folder. Claude will say
  which branch it checked. Comparing across the whole drive is a scheduled job
  for IT, not a chat answer.
- **It sees exactly what you see.** Permissions are unchanged. If you can't open
  a folder in Explorer, neither can Claude — and it won't try to work around it.
  `Z:\OPERATIONS` is one of these: nobody running this can read it.
- **The drive map is a snapshot** (10 Aug 2026, folder names to depth 3) with
  [open questions](../.claude/skills/z-drive-ops/references/z-drive-map.md#open-questions)
  still to settle: how stale is stale, what's in `OPERATIONS`, whether the
  in-region `HANDED OVER` folders should merge into `COMPLETED CONTRACTS`, and
  what to do about ten different archive conventions.
- **"Latest" means most recently changed** — a good clue, not proof of which
  version is authoritative. For anything contractual or priced, a person still
  confirms.

## Quick reference (print or paste this)

> **Getting `Z:` help from Claude**
>
> 1. Open Claude Desktop and sign in with your own account.
> 2. Switch to **Code** mode.
> 3. Pick the project folder **`transpire-claude-code`**
>    (`Z:\CLAUDE CODE\transpire-claude-code`).
> 4. Accept the folder-trust prompt — once only.
> 5. Run `/z-drive-ops` followed by your question, or just ask in normal words.
>    For example:
>    - "where's the latest contract for job 24025?"
>    - "where should I save this signed variation?"
>    - "where does a new subbie's certificate of currency go?"
>    - "any duplicate files in the Gunnedah jobs?"
>
> Say whether a document is **blank or filled in** — blank templates and completed
> ones live in different folders, and that's the most common way to get a wrong
> answer.
>
> It will never move, rename or delete anything without showing you exactly what
> it plans to do and waiting for you to say yes. If it can't find something, give
> it the job number — that works better than the address.

## Maintenance

### Regenerating the staff PDF

The PDF renders from [`z_drive_claude_guide.html`](z_drive_claude_guide.html) in
this folder — edit that, then re-render with headless Chrome:

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="Z:\CLAUDE CODE\transpire-claude-code\docs\Transpire_z_drive_claude_guide.pdf" "file:///Z:/CLAUDE%20CODE/transpire-claude-code/docs/z_drive_claude_guide.html"
```

A courtesy copy is also kept at `Z:\CLAUDE CODE\cowork-projects\2.z_drive\` for
handing to end users outside the repo — re-render to that path too whenever the
HTML changes (point `--print-to-pdf` at it as well), otherwise it drifts from
what staff are reading. The zip file and Markdown copy that used to live
alongside it there were for the old Desktop-attach-a-folder workflow and are no
longer needed — Code mode reads the skill straight from the repo, with nothing
to install per user.

### When the drive changes

If folders are added, renamed, or reorganised, update
[`references/z-drive-map.md`](../.claude/skills/z-drive-ops/references/z-drive-map.md)
inside the skill. The map is what stops Claude guessing at save locations, so a
stale map produces confidently wrong advice.
