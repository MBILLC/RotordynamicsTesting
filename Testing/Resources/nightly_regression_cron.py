#!/usr/bin/env python3
"""Poor-man's cron for this project's regression suite.

Same daemon as ModCheck's own nightly_regression_cron.py (see that repo's
HOWTO.md section 7 for the full investigation) -- no crontab, no systemd, no
root in this JupyterHub single-user container, checked live here again before
building this copy rather than assumed from the other repo's finding. This
script is the closest available equivalent: a long-running Python process
that sleeps until the next scheduled fire time, then runs the regression
suite through run_regression.sh (the one canonical entry point -- see that
script) if, and only if, the repository has changed in the trailing window.

ONLY runs the regression suite. run_regression.sh forwards to
run_regression.py, which never touches RotorDynamics_Credibility.ipynb (a
different repo, Rotordynamics/Resources/Notebooks/) -- this daemon has no
code path that opens, executes, or re-renders that notebook.

Two ways to use it:

  --once   Run exactly one check-and-maybe-simulate cycle right now, then
           exit. This is the reusable "payload" -- point any REAL scheduler
           you do have access to (a Claude Code `schedule` cloud routine, a
           k8s CronJob, an actual crontab on a machine that has one, ...) at
           `nightly_regression_cron.py --once` and it does the right thing
           without needing the perpetual loop below at all.

  (default) Perpetual loop: compute the next occurrence of --hour:--minute
           in --tz, sleep in bounded increments (so a stop request is
           noticed promptly instead of after a multi-hour sleep), then run
           one --once-equivalent cycle and repeat forever. This is the
           fallback for exactly this environment, where nothing else can
           trigger a scheduled run -- see nightly_cron_ctl.sh to start/stop/
           check it. Does NOT survive a JupyterHub server (pod) restart on
           its own -- an ordinary background process, not a system service;
           restart with `./nightly_cron_ctl.sh start` after reopening the
           server.

Default schedule: 22:00 America/New_York, gated on "at least one git commit
in the trailing 24 hours" (see --window-hours), targeting the default
regression_cases.yaml corpus this repo ships (49 RotorDynamics cases).
"""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RES_DIR = Path(__file__).resolve().parent
RUN_SCRIPT = RES_DIR / "run_regression.sh"
LOG_DIR = RES_DIR / "CronLogs"

DEFAULT_HOUR = 22
DEFAULT_MINUTE = 0
DEFAULT_TZ = "America/New_York"
DEFAULT_WINDOW_HOURS = 24.0
# How often the perpetual loop wakes up to re-check the stop flag while
# waiting for the next scheduled fire time -- bounds shutdown latency
# without busy-waiting.
POLL_SECONDS = 60

_stop_requested = False


def _handle_stop(signum, frame):
    global _stop_requested
    _stop_requested = True


def _repo_root() -> Path:
    out = subprocess.run(["git", "-C", str(RES_DIR), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def _log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with open(LOG_DIR / "daemon.log", "a") as f:
        f.write(line + "\n")


def has_recent_changes(repo_root: Path, window_hours: float) -> bool:
    """True if `repo_root` has at least one commit in the trailing `window_hours`."""
    since = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).strftime("%Y-%m-%d %H:%M:%S")
    out = subprocess.run(
        ["git", "-C", str(repo_root), "log", f"--since={since} UTC", "--oneline"],
        capture_output=True, text=True, check=True,
    )
    return bool(out.stdout.strip())


def run_regression_once(extra_args: list[str]) -> tuple[int, Path]:
    """Invoke run_regression.sh, tee output to a timestamped log file, return its exit code."""
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"regression_{stamp}.log"
    with open(log_path, "w") as f:
        proc = subprocess.run([str(RUN_SCRIPT), *extra_args], stdout=f, stderr=subprocess.STDOUT)
    return proc.returncode, log_path


def check_and_maybe_run(window_hours: float, force: bool, extra_args: list[str]) -> None:
    try:
        repo_root = _repo_root()
    except subprocess.CalledProcessError as exc:
        _log(f"ERROR: could not resolve git repo root, skipping cycle: {exc}")
        return

    if not force and not has_recent_changes(repo_root, window_hours):
        _log(f"No commits in the trailing {window_hours:g}h -- skipping regression run.")
        return

    reason = "forced" if force else f"commits found in trailing {window_hours:g}h"
    _log(f"Running regression suite ({reason})...")
    code, log_path = run_regression_once(extra_args)
    verdict = "PASS" if code == 0 else f"FAIL (exit {code})"
    _log(f"Regression run finished: {verdict} -- full log: {log_path}")


def next_fire_time(hour: int, minute: int, tz: ZoneInfo) -> datetime:
    now = datetime.now(tz)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def sleep_until(target: datetime) -> bool:
    """Sleep in POLL_SECONDS increments until `target`. Returns False if a stop was requested."""
    while not _stop_requested:
        remaining = (target - datetime.now(target.tzinfo)).total_seconds()
        if remaining <= 0:
            return True
        time.sleep(min(POLL_SECONDS, remaining))
    return False


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--once", action="store_true",
                    help="run a single check-and-maybe-simulate cycle now, then exit "
                         "(no sleeping/looping) -- use this to test the gate, or as the "
                         "payload for a real external scheduler if one becomes available")
    p.add_argument("--force", action="store_true",
                    help="skip the 'changes in the trailing window' gate and always run")
    p.add_argument("--hour", type=int, default=DEFAULT_HOUR,
                    help=f"fire hour, 24h clock, in --tz (default: {DEFAULT_HOUR})")
    p.add_argument("--minute", type=int, default=DEFAULT_MINUTE,
                    help=f"fire minute (default: {DEFAULT_MINUTE})")
    p.add_argument("--tz", default=DEFAULT_TZ,
                    help=f"IANA timezone name (default: {DEFAULT_TZ!r})")
    p.add_argument("--window-hours", type=float, default=DEFAULT_WINDOW_HOURS,
                    help=f"only run if the repo has a commit in this many trailing "
                         f"hours (default: {DEFAULT_WINDOW_HOURS:g})")
    p.add_argument("extra_args", nargs="*",
                    help="forwarded to run_regression.sh, e.g. -- --case Foo "
                         "--error-log errors.log")
    args = p.parse_args()

    if args.once:
        check_and_maybe_run(args.window_hours, args.force, args.extra_args)
        return

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    tz = ZoneInfo(args.tz)
    _log(f"Nightly regression cron started -- daily {args.hour:02d}:{args.minute:02d} "
         f"{args.tz}, gated on commits in the trailing {args.window_hours:g}h.")
    while not _stop_requested:
        target = next_fire_time(args.hour, args.minute, tz)
        _log(f"Next scheduled run: {target.isoformat()}")
        if not sleep_until(target):
            break
        check_and_maybe_run(args.window_hours, args.force, args.extra_args)
    _log("Nightly regression cron stopped.")


if __name__ == "__main__":
    main()
