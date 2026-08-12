"""Convert an Outlook .msg email to plain text for extract_eoi.py.

Emits headers (From/To/Subject/Date), the plain-text body (falling back to
HTML stripped of tags), and the attachment file names — attachment names
matter because the workflow checks the client ID and plans are attached
(JD-0.1). Read-only; writes only the output text file you name.

Requires: pip install extract-msg

Usage:
    python msg_to_text.py "email.msg" [-o out.txt] [-a attachments_dir]

With -a, every attachment is saved into that directory (inline signature
images included - filter by extension downstream). The EOI PDF and the
inclusions document are attachments, and the workflow needs them (JD-0.1).
"""

import argparse
import os
import re
import sys


def save_attachments(path, outdir):
    import extract_msg
    msg = extract_msg.openMsg(path)
    os.makedirs(outdir, exist_ok=True)
    saved = []
    for att in msg.attachments:
        name = att.longFilename or att.shortFilename or f"unnamed-{len(saved)}"
        name = re.sub(r'[\\/:*?"<>|]', "_", name)
        target = os.path.join(outdir, name)
        data = att.data
        if isinstance(data, bytes):
            with open(target, "wb") as f:
                f.write(data)
            saved.append(target)
        else:  # nested .msg attachment
            try:
                data.export(target if target.endswith(".msg") else target + ".msg")
                saved.append(target)
            except Exception as e:  # keep going; report what failed
                print(f"skipped {name}: {e}", file=sys.stderr)
    msg.close()
    return saved


def msg_to_text(path):
    import extract_msg
    msg = extract_msg.openMsg(path)
    parts = [
        f"From: {msg.sender or ''}",
        f"To: {msg.to or ''}",
        f"Subject: {msg.subject or ''}",
        f"Date: {msg.date or ''}",
        "",
    ]
    body = msg.body
    if not body and msg.htmlBody:
        html = msg.htmlBody
        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="replace")
        html = re.sub(r"<(br|/p|/div|/tr)[^>]*>", "\n", html, flags=re.I)
        html = re.sub(r"<[^>]+>", " ", html)
        body = re.sub(r"[ \t]+", " ", html)
    parts.append(body or "(no body extracted)")
    names = [a.longFilename or a.shortFilename or "(unnamed)"
             for a in msg.attachments]
    if names:
        parts += ["", "Attachments: " + ", ".join(names)]
    msg.close()
    # normalise whitespace: collapse >2 blank lines, strip trailing spaces
    text = "\n".join(parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("msg", help="path to the .msg file")
    ap.add_argument("-o", "--out", help="write text here instead of stdout")
    ap.add_argument("-a", "--attachments",
                    help="also save all attachments into this directory")
    args = ap.parse_args()
    if args.attachments:
        for p in save_attachments(args.msg, args.attachments):
            print(f"attachment: {p}")
    text = msg_to_text(args.msg)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {args.out} ({len(text)} chars)")
    else:
        print(text)
    return 0


# This console is cp1252; document text carries m², ç and dotted leaders, and
# printing any of them would raise UnicodeEncodeError and kill the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
