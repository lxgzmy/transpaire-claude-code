"""FastMCP server: DocuSign drafts with a job's own PDFs. Never sends.

Tools
-----
docusign_token_info     read   environment, account, user, token expiry, write switch
docusign_draft_preview  read   every check the create runs; returns the plan, creates nothing
docusign_create_draft   WRITE  the same checks, then one draft (status "created"), then a read-back

Gates: DOCUSIGN_ENABLE_WRITES (off by default, set in .mcp.json); the host keeps
docusign_create_draft on `ask`, so a person approves every call; and the status
is the constant draft.DRAFT_STATUS. No tool can send, void, correct or delete
an envelope, because client.py has no call that could.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

import httpx

try:
    from mcp.server.fastmcp import FastMCP  # mcp 1.x
except ImportError:  # mcp 2 renamed it; pyproject pins <2, as osc-api does
    from mcp.server.mcpserver import MCPServer as FastMCP

from . import draft
from .auth import AuthError
from .client import DocuSignClient, DocuSignError
from .config import Config, ConfigError, load_config
from .draft import Stop
from .pdfcheck import PdfCheckError, check_pdf

mcp = FastMCP("docusign-upload")

# FastMCP logs at INFO, at which httpx writes every request URL (account and envelope ids)
# into the MCP server log, and that log lives in the user profile on C:. Keep them out.
for _logger in ("httpx", "httpcore"):
    logging.getLogger(_logger).setLevel(logging.WARNING)

DUPLICATE_WINDOW_DAYS = 180

_config: Config | None = None
_config_error: str | None = None
_client: DocuSignClient | None = None

try:
    _config = load_config()
except ConfigError as exc:  # report it at tool-call time, as osc-api does
    _config_error = str(exc)


def _get_client() -> DocuSignClient:
    global _client
    if _client is None:
        _client = DocuSignClient(_config)
    return _client


def _err(text: str, /, **extra: Any) -> dict[str, Any]:
    """Positional-only text, so DocuSign's own `message` can ride along as an extra."""
    out: dict[str, Any] = {"ok": False, "error": text}
    out.update({k: v for k, v in extra.items() if v is not None})
    return out


def _not_configured() -> dict[str, Any]:
    return _err(_config_error or "docusign-upload is not configured.")


def _failure(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, Stop):
        return _err(str(exc), stop=True)
    if isinstance(exc, AuthError):
        return _err(str(exc), consent_url=exc.consent_url)
    if isinstance(exc, DocuSignError):
        return _err(str(exc), status=exc.status, errorCode=exc.error_code, message=exc.detail)
    return _err("Could not reach DocuSign; nothing was created.")


async def _plan(template_name: str, recipients: list[dict[str, str]], email_subject: str,
                email_blurb: str, job_no: str, documents: list[dict[str, str]]) -> draft.Plan:
    """Every check, cheapest first. Raises Stop, AuthError, DocuSignError or httpx.HTTPError."""
    draft.check_text_args(job_no, email_subject, email_blurb)
    kinds = draft.check_kinds([str(d.get("kind", "")) for d in documents])
    files = []
    for kind, item in zip(kinds, documents):
        try:
            files.append((kind, check_pdf(str(item.get("path", "")), _config.upload_roots)))
        except PdfCheckError as exc:
            raise Stop(f"{kind}: {exc}") from None
    client = _get_client()
    raw = draft.pick_template(await client.list_templates(template_name.strip()), template_name)
    template = draft.parse_template(raw)
    sent = draft.check_recipients(recipients, template)
    planned = draft.plan_documents(files, template)
    draft.check_size(planned)
    since = (date.today() - timedelta(days=DUPLICATE_WINDOW_DAYS)).isoformat()
    existing = draft.find_duplicate(await client.list_envelopes(since, f"JobNo={job_no}"), job_no)
    if existing is not None:
        raise Stop(f"an envelope for JobNo {job_no} already exists: {existing.get('envelopeId')} "
                   f"(status {existing.get('status')}). Use that one; nothing new was created.")
    return draft.Plan(template, sent, planned, email_subject, email_blurb, job_no)


async def _read_back(client: DocuSignClient, envelope_id: str, plan: draft.Plan) -> dict[str, Any]:
    return draft.read_back(
        plan,
        envelope=await client.envelope(envelope_id),
        documents=await client.envelope_documents(envelope_id),
        recipients=await client.envelope_recipients(envelope_id),
        custom_fields=await client.envelope_custom_fields(envelope_id),
        template_tabs=draft.tab_counts(await client.template_recipients(plan.template.template_id)),
    )


@mcp.tool()
async def docusign_token_info() -> dict[str, Any]:
    """READ-ONLY. Sign in with JWT and report the environment (SANDBOX or PRODUCTION), the
    account and user names, the token expiry and the write switch with its source. Start here
    to check the connection. A consent error includes the one-time consent URL."""
    if _config is None:
        return _not_configured()
    try:
        session = await _get_client().auth.session()
    except (AuthError, httpx.HTTPError) as exc:
        return _failure(exc)
    return {"ok": True, "environment": _config.label, "account": session.account_name,
            "user": session.user_name,
            "token_expires_in_seconds": max(0, int(session.expires_at - time.monotonic())),
            "config": _config.redacted()}


@mcp.tool()
async def docusign_draft_preview(template_name: str, recipients: list[dict[str, str]],
                                 email_subject: str, email_blurb: str, job_no: str,
                                 documents: list[dict[str, str]]) -> dict[str, Any]:
    """READ-ONLY. Run every check docusign_create_draft runs and return the plan. Creates nothing.

    Args (take them from docusign_envelope.json written by docusign_payload.py):
        template_name: the exact template name (templateName), e.g. "QLD Build _ Single Buyer".
        recipients: buyer-side roles only, [{"role", "name", "email"}] from templateRoles
            (roleName -> role). Never Builder, witnesses or date roles: they keep the template's.
        email_subject, email_blurb: from envelopeDefinition.
        job_no: the JobNo custom field value; used for the duplicate check.
        documents: [{"kind", "path"}] from the documents list; kind is BUILD CONTRACT,
            INCLUSIONS, PRELIMINARY AGREEMENT or PLANS; paths are absolute on this server.

    The plan says, per document, whether the template's tabs carry (same page count) or the
    document goes in untagged and flagged. A stop returns ok=false with stop=true and a reason.
    """
    if _config is None:
        return _not_configured()
    try:
        plan = await _plan(template_name, recipients, email_subject, email_blurb, job_no, documents)
    except (Stop, AuthError, DocuSignError, httpx.HTTPError) as exc:
        return _failure(exc)
    return {"ok": True, "dry_run": True, "environment": _config.label, "plan": draft.plan_view(plan),
            "note": "Nothing was created. docusign_create_draft with the same arguments creates "
                    "this draft."}


@mcp.tool()
async def docusign_create_draft(template_name: str, recipients: list[dict[str, str]],
                                email_subject: str, email_blurb: str, job_no: str,
                                documents: list[dict[str, str]]) -> dict[str, Any]:
    """WRITE (gated). Create ONE DocuSign draft envelope (status "created") from the template with
    the job's own PDFs, then read it back. It never sends: staff check the draft, tag any flagged
    document and send it themselves in DocuSign.

    The host keeps this tool on `ask`, so the approval prompt is the person's yes; do not ask
    again in chat. Same arguments as docusign_draft_preview; it re-runs every check itself.
    Call it once per job. On an error, report it as returned: do not retry, and do not change
    the arguments to make it pass. On "uncertain", run docusign_draft_preview before anything else.
    """
    if _config is None:
        return _not_configured()
    if not _config.enable_writes:
        return _err("Writes are disabled: DOCUSIGN_ENABLE_WRITES is not true for this server "
                    f"(source: {_config.enable_writes_source}). Nothing was created.")
    try:
        plan = await _plan(template_name, recipients, email_subject, email_blurb, job_no, documents)
        body = draft.build_body(plan)
    except (Stop, AuthError, DocuSignError, httpx.HTTPError) as exc:
        return _failure(exc)
    except OSError:
        return _err("A document could not be read on the server; nothing was created.")
    client = _get_client()
    try:
        created = await client.create_draft(body)
    except DocuSignError as exc:
        return _err("DocuSign refused the draft. Reported as returned; not retried.",
                    status=exc.status, errorCode=exc.error_code, message=exc.detail)
    except httpx.HTTPError:
        return _err("The create call failed in transit, so whether a draft exists is uncertain. "
                    "Run docusign_draft_preview with the same arguments (it repeats the duplicate "
                    "check) before trying again.")
    envelope_id = str(created.get("envelopeId", ""))
    result: dict[str, Any] = {"ok": True, "environment": _config.label, "envelopeId": envelope_id,
                              "status": created.get("status"), "plan": draft.plan_view(plan)}
    try:
        result.update(await _read_back(client, envelope_id, plan))
    except (DocuSignError, httpx.HTTPError):
        result["read_back"] = "failed; the draft exists, so check it in DocuSign before sending"
    return result


def main() -> None:
    """Console-script and module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
