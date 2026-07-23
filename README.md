# Transpaire Contract Admin Automation (Claude Code)

Proof-of-concept automation of the contract administration role using Claude Code, running on the client's Windows Server 2022, targeting two workflows:

1. **New Job Creation** — EOI email intake → OnSite Companion (OSC) job creation → Z-Drive folder → DataBuild handoff → contact details → plan-arrival updates.
2. **Variation Stage 1** — variation type decision → OSC variation + workflow templates → Z-Drive Excel variation → OSC document generation → PDF filing → staff alert.

## Documentation

| Doc | Contents |
|---|---|
| [docs/01-solution-architecture.md](docs/01-solution-architecture.md) | Full draft solution: architecture, integration tiers per system, workflow design, HITL, rollout, risks |
| [docs/02-windows-server-setup.md](docs/02-windows-server-setup.md) | Software to install on Windows Server 2022 for the OSC UI-automation skill |
| [docs/03-automation-flow.md](docs/03-automation-flow.md) | How Claude Code, Python UI automation, SQL and import routines fit together at runtime |

## Source workflow documents

- `Contract_Admin_Automation_Analysis.md` — discovery session analysis (client meeting)
- `OSC new job manual.docx` — manual procedure for creating a new job in OnSite Companion
- `CREATING A VARIATION - STAGE 1.pdf` — manual procedure for raising a variation
