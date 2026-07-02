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


CUSTOMER_DEMO_EMAIL = "aarav.customer@finassist-demo.com"
CUSTOMER_DEMO_PASSWORD = "Customer@123"

EMPLOYEE_DEMO_EMAIL = "meera.employee@finassist-demo.com"
EMPLOYEE_DEMO_PASSWORD = "Employee@123"


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


def _demo_user(
    *,
    user_id: str,
    name: str,
    email: str,
    role: str,
    password: str,
    customer_id: Optional[str] = None,
) -> dict:
    password_hash, salt = hash_password(password)

    user = {
        "id": user_id,
        "name": name,
        "email": email.lower().strip(),
        "role": role,
        "salt": salt,
        "password_hash": password_hash,
    }

    if customer_id:
        user["customer_id"] = customer_id

    return user


def ensure_demo_accounts() -> None:
    """
    Ensures stable demo login accounts exist in users.json.

    Why this is needed:
    - customers.json contains loan/customer data only.
    - login validates against users.json.
    - deployed environments may not have manually created demo users.
    - password hashes must match Customer@123 / Employee@123.
    """

    users = read_json("users.json", [])
    customers = read_json("customers.json", [])

    if not isinstance(users, list):
        users = []

    if not isinstance(customers, list):
        customers = []

    demo_emails = {
        CUSTOMER_DEMO_EMAIL,
        EMPLOYEE_DEMO_EMAIL,
        "aarav@example.com",
        "meera.employee@finassist.local",
        "meera.employee@finassist-demo.com",
        "aarav.customer@finassist.local",
    }

    demo_ids = {
        "USR-CUST-DEMO",
        "USR-EMP-DEMO",
    }

    cleaned_users = []

    for user in users:
        email = str(user.get("email", "")).lower().strip()
        user_id = str(user.get("id", "")).strip()

        if email in demo_emails:
            continue

        if user_id in demo_ids:
            continue

        cleaned_users.append(user)

    cleaned_users.append(
        _demo_user(
            user_id="USR-CUST-DEMO",
            name="Aarav Sharma",
            email=CUSTOMER_DEMO_EMAIL,
            role="customer",
            password=CUSTOMER_DEMO_PASSWORD,
            customer_id="CUST001",
        )
    )

    cleaned_users.append(
        _demo_user(
            user_id="USR-EMP-DEMO",
            name="Meera Employee",
            email=EMPLOYEE_DEMO_EMAIL,
            role="employee",
            password=EMPLOYEE_DEMO_PASSWORD,
            customer_id=None,
        )
    )

    write_json("users.json", cleaned_users)

    updated_customers = []
    customer_found = False

    for customer in customers:
        if customer.get("customer_id") == "CUST001":
            customer_found = True
            customer["email"] = CUSTOMER_DEMO_EMAIL
            customer["name"] = customer.get("name") or "Aarav Sharma"
            customer["status"] = customer.get("status") or "active"

        updated_customers.append(customer)

    if not customer_found:
        updated_customers.append(
            {
                "customer_id": "CUST001",
                "name": "Aarav Sharma",
                "registered_mobile": "9876543210",
                "email": CUSTOMER_DEMO_EMAIL,
                "city": "Chennai",
                "status": "active",
                "loans": [
                    {
                        "loan_id": "LN-TW-1001",
                        "product": "Two Wheeler Loan",
                        "vehicle": "Scooter Model X",
                        "principal": 92000,
                        "outstanding": 41650,
                        "emi": 4125,
                        "next_due_date": "2026-07-05",
                        "tenure_months": 24,
                        "paid_emis": 13,
                        "remaining_emis": 11,
                        "status": "regular",
                        "dpd": 0,
                    },
                    {
                        "loan_id": "LN-PL-3310",
                        "product": "Personal Loan",
                        "principal": 150000,
                        "outstanding": 0,
                        "emi": 0,
                        "next_due_date": None,
                        "tenure_months": 18,
                        "paid_emis": 18,
                        "remaining_emis": 0,
                        "status": "closed",
                        "dpd": 0,
                    },
                ],
                "payments": [
                    {
                        "payment_id": "PAY-7741",
                        "loan_id": "LN-TW-1001",
                        "date": "2026-06-05",
                        "amount": 4125,
                        "mode": "UPI",
                        "status": "success",
                        "reference": "UPIXXXX741",
                    },
                    {
                        "payment_id": "PAY-7512",
                        "loan_id": "LN-TW-1001",
                        "date": "2026-05-05",
                        "amount": 4125,
                        "mode": "Auto-debit",
                        "status": "success",
                        "reference": "NACHXXXX512",
                    },
                    {
                        "payment_id": "PAY-7210",
                        "loan_id": "LN-TW-1001",
                        "date": "2026-04-08",
                        "amount": 4250,
                        "mode": "UPI",
                        "status": "success",
                        "reference": "UPIXXXX210",
                        "note": "Included late fee waiver adjustment",
                    },
                ],
                "documents": [
                    {
                        "doc_id": "DOC-101",
                        "name": "Loan Agreement",
                        "loan_id": "LN-TW-1001",
                        "available": True,
                    },
                    {
                        "doc_id": "DOC-102",
                        "name": "NOC",
                        "loan_id": "LN-PL-3310",
                        "available": True,
                    },
                    {
                        "doc_id": "DOC-103",
                        "name": "Repayment Schedule",
                        "loan_id": "LN-TW-1001",
                        "available": True,
                    },
                ],
            }
        )

    write_json("customers.json", updated_customers)


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

    if not isinstance(users, list):
        return None

    email = email.strip().lower()

    return next((u for u in users if str(u.get("email", "")).lower() == email), None)


def create_user(name: str, email: str, password: str) -> dict:
    users = read_json("users.json", [])
    customers = read_json("customers.json", [])

    if not isinstance(users, list):
        users = []

    if not isinstance(customers, list):
        customers = []

    if any(str(u.get("email", "")).lower() == email.lower() for u in users):
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

    if not isinstance(users, list):
        users = []

    user = next((u for u in users if u.get("id") == payload["sub"]), None)

    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return public_user(user)