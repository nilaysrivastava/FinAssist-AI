import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated, Optional, Tuple
from fastapi import Depends, Header, HTTPException
from app.config import APP_SECRET
from app.storage import read_json, write_json


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    salt = salt or secrets.token_urlsafe(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return _b64(dk), salt


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    calc, _ = hash_password(password, salt)
    return hmac.compare_digest(calc, (password_hash or "").rstrip("="))


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "customer_id": user.get("customer_id"),
    }


def find_user_by_email(email: str) -> Optional[dict]:
    users = read_json("users.json", [])
    email = email.strip().lower()
    return next((u for u in users if u["email"].lower() == email), None)


def create_user(name: str, email: str, password: str) -> dict:
    users = read_json("users.json", [])
    customers = read_json("customers.json", [])
    if any(u["email"].lower() == email.lower() for u in users):
        raise HTTPException(status_code=409, detail="Email already exists")
    customer_id = f"CUST{len(customers) + 1:03d}"
    password_hash, salt = hash_password(password)
    user = {
        "id": f"USR-CUST-{len(users) + 1:03d}",
        "name": name.strip(),
        "email": email.strip().lower(),
        "role": "customer",
        "customer_id": customer_id,
        "salt": salt,
        "password_hash": password_hash,
    }
    customer = {
        "customer_id": customer_id,
        "name": name.strip(),
        "registered_mobile": "Not provided",
        "email": email.strip().lower(),
        "city": "Not provided",
        "status": "active",
        "loans": [],
        "payments": [],
        "documents": [],
    }
    users.append(user)
    customers.append(customer)
    write_json("users.json", users)
    write_json("customers.json", customers)
    return user


def issue_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "customer_id": user.get("customer_id"),
        "exp": int(time.time()) + 60 * 60 * 10,
    }
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(APP_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_b64(sig)}"


def decode_token(token: str) -> dict:
    try:
        encoded, sig = token.split(".", 1)
        expected = _b64(hmac.new(APP_SECRET.encode(), encoded.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(encoded))
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def current_user(authorization: Annotated[Optional[str], Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_token(authorization.replace("Bearer ", "", 1))
    users = read_json("users.json", [])
    user = next((u for u in users if u["id"] == payload["sub"]), None)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return public_user(user)
