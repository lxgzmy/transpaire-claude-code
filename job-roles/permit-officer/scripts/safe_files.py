"""Putting a finished file in place on the Z: share, a moment's lock allowed for.

A file just written on the share can be held for a moment by another process (an antivirus scan,
the SMB client), and Windows then refuses the swap or copy with "Access is denied" (WinError 5) or
"being used by another process" (WinError 32). On 27 Nov 2026 that stopped the weekly BA report's
self-check under the scheduled-task wrapper; the same check passed seconds later. Such a refusal is
tried again for about five seconds before it counts; any other error is raised at once.
"""
import os
import shutil
import time

TRIES = 10
WAIT = 0.5  # seconds between tries


def _again(action, tries, wait, sleep):
    for n in range(tries):
        try:
            action()
            return n  # how many retries it took
        except PermissionError:
            if n == tries - 1:
                raise
            sleep(wait)


def replace(src, dst, tries=TRIES, wait=WAIT, _replace=os.replace, _sleep=time.sleep):
    """os.replace(src, dst), retried while the share holds either file."""
    return _again(lambda: _replace(src, dst), tries, wait, _sleep)


def copy(src, dst, tries=TRIES, wait=WAIT, _copy=shutil.copyfile, _sleep=time.sleep):
    """shutil.copyfile(src, dst), retried while the share holds either file."""
    return _again(lambda: _copy(src, dst), tries, wait, _sleep)
