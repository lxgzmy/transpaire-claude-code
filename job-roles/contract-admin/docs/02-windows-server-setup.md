# Windows Server 2022 Setup — OSC UI-Automation Skill

Software and configuration required on the client's Windows Server 2022 to run the OSC skill (UI automation of OnSite Companion) and supporting skills.

## Core agent

| Component | Purpose | Notes |
|---|---|---|
| **Claude Code** (native Windows) | Orchestrator / agent runtime | Requires Git for Windows (bundled bash). Do **not** use WSL — the OSC skill must drive native Windows GUI apps in the interactive desktop session |
| **Node.js 18+** | Claude Code runtime, MCP servers via `npx` | |
| **Git for Windows** | Claude Code dependency + skills repo checkout | |

## UI automation layer (Python)

| Component | Purpose | Notes |
|---|---|---|
| **Python 3.11+** | Step-script runtime | |
| `pywinauto` | Primary UI driver | OSC is a legacy VB app — test both the `win32` (MFC/VB) and `uia` backends against OSC's controls; grids (e.g. Variation Activities list) often need `win32` |
| `pyautogui` | Pixel-level fallback | For controls not exposed to pywinauto |
| `Pillow` / `mss` | Per-step verification screenshots | Feeds the evidence log |
| `pywin32` | Windows COM/API | Also used by the Z-Drive skill (Excel variation fill, Word → PDF export via Office COM) |

Optional alternative driver: **Windows Application Driver (WinAppDriver)** + Appium — usually unnecessary; pywinauto is simpler for a legacy VB app.

## Inspection tooling (build-time only)

- **Accessibility Insights for Windows** or **Inspect.exe** (Windows SDK) — map OSC's window/control tree when building the step library.
- pywinauto `print_control_identifiers()` — same purpose, scriptable.

## Session requirements (critical)

UI automation only works in an **unlocked, interactive desktop session**:

- Dedicated Windows service account logged into the **console session**, or an RDP session configured to stay active on disconnect (`tscon` redirect or group policy so the session never locks).
- Disable screen lock / screensaver for that account.
- Fixed display resolution (e.g. 1920×1080) so coordinates and screenshots are deterministic.
- OnSite Companion installed and pre-authenticated under that account.
- **Z: drive mapped in that session** (SMB mapping is per-session, not machine-wide).

## Supporting pieces

- **Task Scheduler** (or NSSM as a service wrapper) — run the orchestrator / email-intake agent on schedule.
- **Microsoft Data API Builder** (`dotnet tool install Microsoft.DataApiBuilder`, requires .NET 8) — read-only REST/MCP layer over the DataBuild SQL Server DB (Tier 1 of the DataBuild adapter).
- **Microsoft Office** (Excel/Word) — already present for staff; needed for COM automation and OSC's Generate Document flow.

## Early validation item

Verify whether OSC exposes proper Win32/UIA control identifiers. If its grids are owner-drawn (custom-painted), pywinauto cannot read them and the skill must lean on Claude's computer-use vision (screenshot → coordinate click), which is slower and makes the fixed-resolution session mandatory. This is exactly what the "validate OSC integration surface first" rollout step should test on a demo job.
