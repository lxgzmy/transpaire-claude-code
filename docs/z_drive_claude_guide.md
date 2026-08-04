# Z: drive help with Claude — user guide

Using Claude to find, file and tidy things on the `Z:` shared drive. Written for
everyday use by anyone in the company, technical or not.

The skill behind it: [`.claude/skills/z-drive-ops/`](../.claude/skills/z-drive-ops/SKILL.md).

**What it does, in one line:** you ask "where's the latest variation for 26049?"
or "where should this colour selection go?" and it answers with a path you can
paste into Explorer.

## Two ways to use it

| | Claude Code (server) | Claude Desktop (your own PC) |
|---|---|---|
| Who it suits | Technical / power users | **Everyone else** |
| How to start | `/z-drive-ops <what you want>` | Just ask in plain English |
| Sees `Z:` via | The mapped drive in that login session | A folder you attach |
| Big scans, duplicate hunts by content | Yes | No — targeted searches only |
| Best for | Whole-drive sweeps, new job folder trees | Everyday "where is / where do I put this" |

Both use the same skill, so the advice is consistent either way.

## Claude Code (already set up)

The skill lives in this repo at `.claude/skills/z-drive-ops/`. Nothing to
install. From a session started at the repo root:

```
/z-drive-ops where should a signed variation for 26049 go?
```

It also activates on its own when a request is clearly about the drive.

## Claude Desktop, step by step

### The one thing that must be right: on your computer, not the cloud

Claude Desktop can run a task **on your computer** or **in the cloud**. `Z:` is a
network share inside the office, so:

- **On your computer** → can see `Z:`. ✅
- **In the cloud** → cannot see `Z:`, and never will. ❌

Always choose **"On your computer"**. If a session says it can't find `Z:` or the
folder isn't there, this is nearly always why. (Confirmed the hard way: a cloud
session couldn't reach the share as a drive letter or as `\\server\share`.)

### Step 1 — package the skill (IT, once)

In PowerShell on the server:

```powershell
Compress-Archive -Path 'Z:\CLAUDE CODE\transpaire-claude-code\.claude\skills\z-drive-ops' -DestinationPath "$env:USERPROFILE\Desktop\z-drive-ops.zip" -Force
```

That writes `z-drive-ops.zip` to the Desktop with the `z-drive-ops` folder inside
it — the structure Claude requires. A ready-made copy is also kept at
`Z:\CLAUDE CODE\cowork-projects\2.z_drive\`.

Re-run the command and re-upload after any change to the skill.

### Step 2 — add it to Claude Desktop (each user, once)

1. Open **Claude Desktop**.
2. Go to **Settings → Capabilities** (also reachable via **Customize** in the
   sidebar).
3. **Upload** `z-drive-ops.zip`.
4. Check it's **enabled**.

Skills belong to your Claude account rather than the machine, so it follows you
to another PC — but `Z:` still has to be reachable from wherever you are.

### Step 3 — attach the drive (each session, about five seconds)

Start a task **on your computer**, then attach a folder with the folder picker:

- **`Z:\PROJECTS`** for job work — the recommended default.
- **`Z:\`** only if you also need the department folders.

Worth knowing:
- Only **you** can attach a folder. Claude can't reach outside what you attach
  and can't attach anything itself. That's the security boundary.
- Use the mapped letter (`Z:\`). `\\server\share` paths aren't supported, so map
  the drive first — which is how staff already use it.
- Attach the narrowest folder that covers the job. The `Z:\` root also holds
  accounts, staff and password folders that don't need to be in scope. The skill
  refuses to read the credentials folder either way, but not attaching it is
  better.

### Step 4 — just ask

No commands to learn:

> where's the latest variation for 26049?
> I've got a signed colour selection for 26049 — where does it go?
> is there more than one copy of the contract for 26049?
> find anything for lot 5 pearson street

## First-time walkthrough

Five things to try, in order, and what to notice about each.

1. **Find something** — *"where's the latest variation for job 26049?"*
   It gives a full path, says which date it went by, and points out that the date
   doesn't prove it's the signed copy.
2. **Ask where something goes** — *"I've got a new colour selection form for
   26049, where should I save it?"* It recommends a folder **and** matches the
   naming style of the files already in there.
3. **Ask for a tidy check** — *"any duplicates in the GUNNEDAH jobs?"*
   It reports what it found and changes nothing.
4. **Ask it to act** — *"just delete the duplicates for me"*
   It shows the exact list and asks first. This is the important one: it never
   quietly moves or deletes anyone's files.
5. **Try a blocked folder** — ask for something in
   `Z:\COMPANY GENERAL INFORMATION\TRANSPIRE PASSWORDS & SET UP WORKFLOW`.
   It refuses and explains why.

If you're walking someone else through this, pick a job number you've checked
actually has files in it.

## Limits, stated plainly

- **Cloud sessions can't see `Z:`.** On your computer only.
- **No scripts against `Z:` from Desktop.** Claude's code sandbox has no
  network-drive access, so comparing thousands of files by content, or sweeping
  the whole drive, belongs in Claude Code on the server. Everyday searching is
  unaffected.
- **It sees exactly what you see.** Permissions are unchanged. If you can't open
  a folder in Explorer, neither can Claude — and it won't try to work around it.
- **The drive map is a snapshot** (4 Aug 2026, folder names only) with
  [open questions](../.claude/skills/z-drive-ops/references/z-drive-map.md#open-questions)
  still to settle: how stale is stale, which of the two `ESTATES INFORMATION`
  folders is current, and what to do about four different archive conventions.
- **"Latest" means most recently changed** — a good clue, not proof of which
  version is authoritative. For anything contractual or priced, a person still
  confirms.

## Quick reference (print or paste this)

> **Getting `Z:` help from Claude**
>
> 1. Open Claude Desktop, start a task **On your computer**.
> 2. Attach the folder `Z:\PROJECTS`.
> 3. Ask in normal words. For example:
>    - "where's the latest contract for job 26049?"
>    - "where should I save this variation?"
>    - "any duplicate files in the Gunnedah jobs?"
>
> It will never move, rename or delete anything without showing you exactly what
> it plans to do and waiting for you to say yes. If it can't find something, give
> it the job number — that works better than the address.
