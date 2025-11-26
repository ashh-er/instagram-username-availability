import argparse
import functools
import sys
import itertools
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import requests
import json
import os
import atexit
import signal

ALLOWED = "abcdefghijklmnopqrstuvwxyz0123456789._"
THREADS = 5  # adjust for faster/slower
MIN_LEN = 1
MAX_LEN = 4  # can be increased to 30

output_lock = threading.Lock()

# Checkpointing globals
CHECKPOINT_FILE = ".instagram_checkpoint.json"
last_checked = None
last_checked_lock = threading.Lock()
_saver_thread = None
_saver_stop = threading.Event()
_SAVER_INTERVAL = 5.0  # seconds


def load_checkpoint():
    """Load last-checked username from checkpoint file, or return None."""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last")
    except Exception:
        pass
    return None


def save_checkpoint():
    """Save the last-checked username to checkpoint file (best-effort)."""
    try:
        with last_checked_lock:
            data = {"last": last_checked}
        # write atomically
        tmp = CHECKPOINT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, CHECKPOINT_FILE)
    except Exception:
        pass


def _saver_thread_func():
    while not _saver_stop.wait(_SAVER_INTERVAL):
        save_checkpoint()


def start_checkpoint_saver():
    global _saver_thread
    if _saver_thread is None or not _saver_thread.is_alive():
        _saver_stop.clear()
        _saver_thread = threading.Thread(target=_saver_thread_func, daemon=True)
        _saver_thread.start()


def stop_checkpoint_saver():
    _saver_stop.set()
    if _saver_thread is not None:
        _saver_thread.join(timeout=1.0)


def _handle_exit(signum=None, frame=None):
    try:
        stop_checkpoint_saver()
    except Exception:
        pass
    try:
        save_checkpoint()
    except Exception:
        pass


# register atexit and common signals
atexit.register(_handle_exit)
try:
    signal.signal(signal.SIGTERM, _handle_exit)
except Exception:
    # Windows may not have SIGTERM in some contexts
    pass


# -----------------------------
# IG username rules
# -----------------------------
def is_valid_instagram_username(username):
    if not (MIN_LEN <= len(username) <= MAX_LEN):
        return False
    if username.startswith(".") or username.endswith("."):
        return False
    if ".." in username:
        return False
    for c in username:
        if c not in ALLOWED:
            return False
    return True


# -----------------------------
# Username generator
# -----------------------------
def generate_usernames(start_after=None):
    """Generate usernames lexicographically. If `start_after` is provided,
    skip until that username has been seen, then resume after it.
    """
    started = start_after is None
    for length in range(MIN_LEN, MAX_LEN + 1):
        for combo in itertools.product(ALLOWED, repeat=length):
            username = "".join(combo)
            if not is_valid_instagram_username(username):
                continue
            if not started:
                if username == start_after:
                    # we've reached the checkpoint; next one should be yielded
                    started = True
                continue
            yield username


# -----------------------------
# Check username availability
# -----------------------------
def check_username(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
            "Mozilla/5.0 (Linux; Android 11)"
        ])
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 404:
            return "available"
        elif r.status_code == 200:
            return "taken"
        elif r.status_code in (403, 429):
            return "blocked"
        else:
            return "unknown"
    except Exception:
        return "error"


# -----------------------------
# Worker function for threads
# -----------------------------
def worker(username_generator, output_file):
    while True:
        try:
            username = next(username_generator)
        except StopIteration:
            return

        # record progress (best-effort)
        with last_checked_lock:
            global last_checked
            last_checked = username

        result = check_username(username)

        if result == "available":
            print(f"[AVAILABLE] {username}")
            with output_lock:
                output_file.write(username + "\n")
                output_file.flush()
                # ensure checkpoint is saved so we don't re-check this next run
                try:
                    save_checkpoint()
                except Exception:
                    pass
        elif result == "taken":
            print(f"[TAKEN] {username}")
        elif result == "blocked":
            print("[RATE LIMIT] Sleeping 90 seconds...")
            time.sleep(90)
            continue

        # Random delay to avoid getting blocked
        time.sleep(random.uniform(0.8, 1.5))


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Instagram Username Checker")
    parser.add_argument('--threads', type=int, default=THREADS, help='Number of threads')
    args = parser.parse_args()

    # Load checkpoint and start saver
    start_after = load_checkpoint()
    start_checkpoint_saver()

    try:
        usernames = generate_usernames(start_after=start_after)
        usernames = iter(usernames)

        with open("available_instagram.txt", "a", encoding="utf-8") as output_file:
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                for _ in range(args.threads):
                    executor.submit(worker, usernames, output_file)
    finally:
        # Ensure final save and stop background thread
        try:
            stop_checkpoint_saver()
        except Exception:
            pass
        try:
            save_checkpoint()
        except Exception:
            pass


if __name__ == "__main__":
    main()
