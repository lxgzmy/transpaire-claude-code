"""Convert an Outlook .msg email to plain text for extract_eoi.py.

Emits headers (From/To/Subject/Date), the plain-text body (falling back to
HTML stripped of tags), and the attachment file names — attachment names
matter because the workflow checks the client ID and plans are attached
(JD-0.1). Read-only; writes only the output text file you name.

Requires: pip install extract-msg

Usage:
    python msg_to_text.py "email.msg" [-o out.txt]
"""

import argparse
import re
import sys


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
    args = ap.parse_args()
    text = msg_to_text(args.msg)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {args.out} ({len(text)} chars)")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
