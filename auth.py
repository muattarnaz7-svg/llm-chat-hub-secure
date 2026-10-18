"""Email + secret code login (file based, local).

- Code kabhi seedha save nahi hota, sirf PBKDF2 hash (salt ke saath).
- 5 ghalat koshishon ke baad 5 minute ka lock.
- Optional: SIGNUP_CODE (env) set ho to naya account sirf wohi bana sakta hai
  jise ye invite code pata ho (public deploy par apni API quota bachane ke liye).
- Users ki file: users.json (isay GitHub par push na karein, .gitignore mein daalein).
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

USERS_FILE = Path(os.getenv("USERS_FILE", "users.json"))
PBKDF2_ROUNDS = 200_000
MIN_CODE_LENGTH = 6
MAX_FAILED = 5
LOCK_SECONDS = 300

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_lock = threading.Lock()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def _load() -> dict:
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(users: dict) -> None:
    tmp = USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2), encoding="utf-8")
    os.replace(tmp, USERS_FILE)


def _hash(code: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt, PBKDF2_ROUNDS).hex()


def user_exists(email: str) -> bool:
    return normalize_email(email) in _load()


def user_prefix(email: str) -> str:
    """Chat ids ke shuru mein lagta hai taake har user ki chats alag rahein."""
    digest = hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()
    return f"u{digest[:12]}_"


def signup_code_required() -> bool:
    return bool(os.getenv("SIGNUP_CODE"))


def register(email: str, code: str, invite: str = "") -> tuple[bool, str]:
    email = normalize_email(email)
    if not is_valid_email(email):
        return False, "Sahi email likhein."
    if len(code) < MIN_CODE_LENGTH:
        return False, f"Code kam az kam {MIN_CODE_LENGTH} characters ka hona chahiye."

    required = os.getenv("SIGNUP_CODE", "")
    if required and not hmac.compare_digest(invite.encode(), required.encode()):
        return False, "Invite code galat hai."

    with _lock:
        users = _load()
        if email in users:
            return False, "Ye email pehle se registered hai."
        salt = secrets.token_bytes(16)
        users[email] = {
            "salt": salt.hex(),
            "hash": _hash(code, salt),
            "created": int(time.time()),
            "failed": 0,
            "locked_until": 0,
        }
        _save(users)
    return True, ""


def verify(email: str, code: str) -> tuple[bool, str]:
    email = normalize_email(email)
    generic_error = "Code galat hai."
    with _lock:
        users = _load()
        user = users.get(email)
        if user is None:
            return False, generic_error

        now = time.time()
        locked_until = user.get("locked_until", 0)
        if locked_until > now:
            minutes = int((locked_until - now) // 60) + 1
            return False, f"Bohat ghalat koshishein. {minutes} minute baad dobara try karein."

        expected = user["hash"]
        actual = _hash(code, bytes.fromhex(user["salt"]))
        if hmac.compare_digest(actual, expected):
            if user.get("failed"):
                user["failed"] = 0
                _save(users)
            return True, ""

        user["failed"] = user.get("failed", 0) + 1
        if user["failed"] >= MAX_FAILED:
            user["failed"] = 0
            user["locked_until"] = now + LOCK_SECONDS
        _save(users)
        return False, generic_error