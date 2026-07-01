import re
from typing import List, Optional, Tuple

CUSTOMER_ID_RE = re.compile(r"\bCUST\d{3,}\b", re.I)
LOAN_ID_RE = re.compile(r"\bLN-[A-Z0-9-]{4,}\b", re.I)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
MOBILE_RE = re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|db[_-]?password|system[_-]?prompt)\b\s*[:=]\s*[^\s,;]+"
)

SECRET_PATTERNS = [
    r"api[_ -]?key",
    r"db[_ -]?password",
    r"database credential",
    r"system prompt",
    r"developer message",
    r"hidden instruction",
    r"chain of thought",
    r"internal secret",
    r"confidential integration",
    r"production credential",
    r"otp",
    r"cvv",
    r"upi pin",
    r"net banking password",
    r"full card number",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|above|system) instructions",
    r"act as (dan|developer|root|admin)",
    r"jailbreak",
    r"developer mode",
    r"reveal your prompt",
    r"bypass (policy|guardrail|access)",
    r"no guardrail",
    r"do anything now",
    r"print hidden",
    r"show me your tools",
]

CRITICAL_ACTION_PATTERNS = [
    r"waive|waiver",
    r"refund",
    r"settlement",
    r"legal notice",
    r"repossession",
    r"police|fraud|harassment",
    r"change registered mobile|change mobile|change email|update kyc",
    r"close my loan now|foreclose now|final foreclosure amount|foreclosure quote",
    r"remove penalty|reverse charge|delete charge",
    r"approve|sanction|disburse",
]


def extract_customer_ids(text: str) -> List[str]:
    return [m.upper() for m in CUSTOMER_ID_RE.findall(text or "")]


def has_secret_request(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in SECRET_PATTERNS)


def has_prompt_injection(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in PROMPT_INJECTION_PATTERNS)


def looks_critical(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in CRITICAL_ACTION_PATTERNS)


def redact_pii(text: str) -> str:
    if not text:
        return text
    text = SECRET_VALUE_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = EMAIL_RE.sub(lambda m: _mask_email(m.group(0)), text)
    text = MOBILE_RE.sub(lambda m: _mask_mobile(m.group(0)), text)
    text = AADHAAR_RE.sub("XXXX-XXXX-XXXX", text)
    text = PAN_RE.sub("XXXXX0000X", text)
    text = CARD_RE.sub(lambda m: _mask_card(m.group(0)), text)
    return text


def _mask_email(email: str) -> str:
    user, _, domain = email.partition("@")
    if len(user) <= 2:
        masked = user[:1] + "***"
    else:
        masked = user[:2] + "***"
    return masked + "@" + domain


def _mask_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 10:
        return digits[:2] + "XXXXXX" + digits[-2:]
    return "[masked mobile]"


def _mask_card(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 13:
        return value
    return "XXXX-XXXX-XXXX-" + digits[-4:]


def static_safety_block(message: str, user: dict) -> Tuple[bool, Optional[str]]:
    if len(message) > 3000:
        return True, "Your message is too long for this support chat. Please shorten it."
    if has_secret_request(message) or has_prompt_injection(message):
        return True, "I can’t help with requests to reveal hidden prompts, credentials, OTPs, passwords, UPI PINs, CVV, or confidential internal information."
    ids = extract_customer_ids(message)
    if user.get("role") == "customer":
        own = (user.get("customer_id") or "").upper()
        if any(cid != own for cid in ids):
            return True, "I can’t access or discuss another customer’s records. Please ask about your own logged-in account."
    return False, None
