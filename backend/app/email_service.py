import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import DATA_DIR


OFFERS_FILE = Path(DATA_DIR) / "email_offers.json"
OUTBOX_FILE = Path(DATA_DIR) / "email_outbox.json"

RECENT_ANY_OFFER_WINDOW_SECONDS = 90
RECENT_CATEGORY_OFFER_WINDOW_SECONDS = 8 * 60


SMALLTALK_RE = re.compile(
    r"^(h+i+|h+e+y+|h+e+l+o+|h+l+o+|yo+|yoo+|ok+|okay+|okk+|okayy+|thanks?|thank you|no worries|no problem|nice|great|good|cool|wow+|haha+|hehe+|bye)[\s!.?]*$",
    re.I,
)


def _read_list(path: Path) -> List[dict]:
    try:
        if not path.exists():
            return []

        data = json.loads(path.read_text(encoding="utf-8"))

        return data if isinstance(data, list) else []

    except Exception:
        return []


def _write_list(path: Path, data: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _mask_email(email: Optional[str]) -> str:
    email = email or ""

    if "@" not in email:
        return "registered email"

    local, domain = email.split("@", 1)

    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"

    return f"{local[:2]}***@{domain}"


def _clean(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _tool_names(tool_trace: List[dict]) -> set:
    return {str(t.get("tool") or "") for t in (tool_trace or []) if t.get("tool")}


def _is_definition_only(message: str) -> bool:
    text = _clean(message)

    return bool(re.match(r"^(what is|what's|define|meaning of)\s+noc\s*$", text))


def _is_explicit_email_request(message: str) -> bool:
    text = _clean(message)

    explicit_terms = [
        "email me",
        "mail me",
        "send email",
        "send mail",
        "send it to email",
        "send it to mail",
        "send this to email",
        "send this to mail",
        "send details to email",
        "send details to mail",
    ]

    return any(term in text for term in explicit_terms)


def _is_simple_account_fact_question(message: str) -> bool:
    text = _clean(message)

    simple_terms = [
        "what is my next emi due date",
        "next emi due date",
        "my next emi due date",
        "emi due date",
        "when is my next emi",
        "when is the next emi",
        "what is my emi amount",
        "emi amount",
        "amount for the next one",
        "what is the amount for the next one",
        "show my recent payment status",
        "recent payment status",
        "recent payments",
        "payment records",
        "last payment",
        "last deducted",
        "last payment amount",
        "is my loan closed",
        "loan closed",
        "loan closure status",
        "vehicle loan",
        "vehicle load",
        "two wheeler loan",
        "two wheeler load",
        "my vehicle loan",
        "my vehicle load",
    ]

    if any(term in text for term in simple_terms):
        return True

    if re.search(r"\b(next|due|amount|status|closed|active)\b", text) and re.search(r"\b(emi|loan|payment)\b", text):
        return True

    return False


def _looks_like_weak_or_error_answer(answer: str) -> bool:
    ans = _clean(answer)

    weak_phrases = [
        "i could not find enough",
        "i couldn't find enough",
        "not enough information",
        "current knowledge base to answer",
        "backend connection was interrupted",
        "request failed",
        "internal server error",
        "could you please clarify",
        "did you mean",
    ]

    return any(phrase in ans for phrase in weak_phrases)


def _is_hard_no_email(
    message: str,
    answer: str,
    sources: List[dict],
    tool_trace: List[dict],
    blocked: bool,
) -> bool:
    if blocked:
        return True

    msg = _clean(message)
    ans = _clean(answer)
    tools = _tool_names(tool_trace)

    if _is_explicit_email_request(message):
        return False

    if SMALLTALK_RE.match(msg):
        return True

    if _is_definition_only(message):
        return True

    if _is_simple_account_fact_question(message):
        return True

    if _looks_like_weak_or_error_answer(answer):
        return True

    if not tools and not sources:
        return True

    if any(
        phrase in ans
        for phrase in [
            "you're welcome",
            "glad that helped",
            "have a great day",
            "please keep the conversation respectful",
            "could you please clarify",
            "did you mean",
        ]
    ):
        return True

    return False


def _recent_offer_exists(current_user: dict, category: str) -> bool:
    user_id = current_user.get("id")

    if not user_id:
        return False

    now = int(time.time())
    offers = _read_list(OFFERS_FILE)

    for offer in reversed(offers[-60:]):
        if offer.get("user_id") != user_id:
            continue

        created_at = int(offer.get("created_at") or 0)
        age = now - created_at

        if age <= RECENT_ANY_OFFER_WINDOW_SECONDS:
            return True

        if category and offer.get("category") == category and age <= RECENT_CATEGORY_OFFER_WINDOW_SECONDS:
            return True

    return False


def _should_offer_email(
    message: str,
    answer: str,
    current_user: dict,
    sources: List[dict],
    tool_trace: List[dict],
    blocked: bool = False,
    needs_human_approval: bool = False,
) -> Dict[str, Any]:
    if current_user.get("role") != "customer":
        return {"offer_email": False, "category": "", "subject": ""}

    if _is_hard_no_email(message, answer, sources, tool_trace, blocked):
        return {"offer_email": False, "category": "", "subject": ""}

    msg = _clean(message)
    tools = _tool_names(tool_trace)
    answer_words = len((answer or "").split())

    account_tools = {"get_customer_profile", "get_customer_loans", "get_payment_history"}

    if needs_human_approval:
        return {
            "offer_email": True,
            "category": "human_approval_summary",
            "subject": "FinAssist human review request summary",
        }

    if "create_support_ticket" in tools:
        return {
            "offer_email": True,
            "category": "support_ticket_summary",
            "subject": "FinAssist support ticket summary",
        }

    account_summary_terms = [
        "account summary",
        "summary of my account",
        "what do you know about me",
        "about me",
        "my whole account",
        "my full account",
        "my complete account",
        "all details",
        "full details",
    ]

    if tools & account_tools and any(term in msg for term in account_summary_terms):
        return {
            "offer_email": True,
            "category": "account_summary",
            "subject": "FinAssist loan and account summary",
        }

    payment_issue_terms = [
        "debited but not reflected",
        "payment not reflected",
        "money debited",
        "amount debited",
        "duplicate debit",
        "payment failed",
        "failed payment",
        "reconciliation",
        "what should i do",
    ]

    if ("get_payment_history" in tools or sources) and any(term in msg for term in payment_issue_terms) and answer_words >= 45:
        return {
            "offer_email": True,
            "category": "payment_guidance",
            "subject": "FinAssist payment support guidance",
        }

    noc_how_to_terms = [
        "download my noc",
        "get my noc",
        "apply for my noc",
        "how can i download",
        "how do i download",
        "how can i get",
        "how do i get",
        "how to apply",
        "foreclosure",
        "pre closure",
        "pre-closure",
    ]

    if sources and any(term in msg for term in noc_how_to_terms) and answer_words >= 55:
        return {
            "offer_email": True,
            "category": "noc_or_foreclosure_guidance",
            "subject": "FinAssist NOC and loan-closure guidance",
        }

    policy_how_to_terms = [
        "how",
        "process",
        "steps",
        "not reflected",
        "document",
        "documents",
        "portal",
        "policy",
    ]

    if sources and any(term in msg for term in policy_how_to_terms) and answer_words >= 70:
        return {
            "offer_email": True,
            "category": "policy_guidance",
            "subject": "FinAssist support guidance summary",
        }

    return {"offer_email": False, "category": "", "subject": ""}


def _source_lines(sources: List[dict]) -> str:
    if not sources:
        return ""

    lines = ["\nSources used:"]

    for source in sources[:5]:
        title = source.get("title") or source.get("id") or "Source"
        section = source.get("section") or source.get("category") or ""
        lines.append(f"- {title}{(' · ' + section) if section else ''}")

    return "\n".join(lines)


def create_email_offer(
    message: str,
    answer: str,
    current_user: dict,
    sources: Optional[List[dict]] = None,
    tool_trace: Optional[List[dict]] = None,
    blocked: bool = False,
    needs_human_approval: bool = False,
) -> Optional[dict]:
    sources = sources or []
    tool_trace = tool_trace or []

    decision = _should_offer_email(
        message=message,
        answer=answer,
        current_user=current_user,
        sources=sources,
        tool_trace=tool_trace,
        blocked=blocked,
        needs_human_approval=needs_human_approval,
    )

    if not decision.get("offer_email"):
        return None

    category = str(decision.get("category") or "")

    if not _is_explicit_email_request(message) and _recent_offer_exists(current_user, category):
        return None

    email = current_user.get("email") or ""

    if not email:
        return None

    offer_id = f"email_{uuid4().hex[:12]}"
    now = int(time.time())

    email_body = (
        f"Hello {current_user.get('name', 'Customer')},\n\n"
        "Here is the FinAssist AI summary you requested:\n\n"
        f"Your question:\n{message}\n\n"
        f"Answer:\n{answer}\n"
        f"{_source_lines(sources)}\n\n"
        "Regards,\nFinAssist AI"
    )

    record = {
        "offer_id": offer_id,
        "user_id": current_user.get("id"),
        "customer_id": current_user.get("customer_id"),
        "recipient": email,
        "recipient_masked": _mask_email(email),
        "subject": decision.get("subject") or "FinAssist AI summary",
        "category": category,
        "message": message,
        "answer": answer,
        "sources": sources,
        "email_body": email_body,
        "status": "pending_confirmation",
        "created_at": now,
    }

    offers = _read_list(OFFERS_FILE)
    offers.append(record)
    _write_list(OFFERS_FILE, offers)

    return {
        "offer_id": offer_id,
        "title": "Email this summary?",
        "message": f"Would you like me to send these details to your registered email ({_mask_email(email)})?",
        "recipient_masked": _mask_email(email),
        "category": category,
    }


def send_email_offer(offer_id: str, current_user: dict) -> dict:
    offers = _read_list(OFFERS_FILE)
    target = None

    for offer in offers:
        if offer.get("offer_id") == offer_id:
            target = offer
            break

    if not target:
        return {"allowed": False, "reason": "Email offer not found."}

    if target.get("user_id") != current_user.get("id"):
        return {"allowed": False, "reason": "This email offer does not belong to the current user."}

    if target.get("status") == "sent":
        return {
            "allowed": True,
            "message": "This summary was already sent.",
            "email_id": target.get("email_id"),
            "recipient_masked": target.get("recipient_masked"),
        }

    email_id = f"outbox_{uuid4().hex[:12]}"
    now = int(time.time())

    outbox = _read_list(OUTBOX_FILE)
    outbox.append(
        {
            "email_id": email_id,
            "offer_id": offer_id,
            "recipient": target.get("recipient"),
            "recipient_masked": target.get("recipient_masked"),
            "subject": target.get("subject"),
            "body": target.get("email_body"),
            "status": "sent_mock",
            "created_at": now,
        }
    )
    _write_list(OUTBOX_FILE, outbox)

    target["status"] = "sent"
    target["email_id"] = email_id
    target["sent_at"] = now
    _write_list(OFFERS_FILE, offers)

    return {
        "allowed": True,
        "message": f"Email sent to {target.get('recipient_masked')}.",
        "email_id": email_id,
        "recipient_masked": target.get("recipient_masked"),
    }
