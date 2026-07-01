import time
import uuid
from typing import Optional, Tuple
from app.memory import get_user_memory, save_conversation_memory
from app.rag import search_kb
from app.security import looks_critical, redact_pii
from app.storage import append_json_list, read_json


def mask_mobile(mobile: Optional[str]) -> str:
    if not mobile or len(mobile) < 4:
        return "masked"
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if len(digits) >= 10:
        return digits[:2] + "XXXXXX" + digits[-2:]
    if "X" in mobile:
        return mobile
    return "masked"


def mask_email(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return "masked"
    user, domain = email.split("@", 1)
    return (user[:2] + "***@" + domain) if len(user) > 2 else (user[:1] + "***@" + domain)


def _customers():
    return read_json("customers.json", [])


def _find_customer(customer_id: str) -> Optional[dict]:
    customer_id = (customer_id or "").upper().strip()
    return next((c for c in _customers() if c.get("customer_id", "").upper() == customer_id), None)


def _allowed_customer_access(current_user: dict, customer_id: str) -> Tuple[bool, Optional[str]]:
    customer_id = (customer_id or "").upper().strip()
    if not customer_id:
        return False, "Customer ID is required."
    if current_user.get("role") == "employee":
        return True, None
    own = (current_user.get("customer_id") or "").upper()
    if customer_id != own:
        return False, "Access denied: customers can access only their own logged-in records."
    return True, None


def _safe_customer_profile(c: dict, role: str) -> dict:
    return {
        "customer_id": c.get("customer_id"),
        "name": c.get("name"),
        "city": c.get("city"),
        "status": c.get("status"),
        "registered_mobile": mask_mobile(c.get("registered_mobile")),
        "email": mask_email(c.get("email")),
        "loan_count": len(c.get("loans", [])),
        "document_count": len(c.get("documents", [])),
    }


def search_knowledge_base(query: str, current_user: dict, top_k: int = 6) -> dict:
    results = search_kb(query=query, role=current_user.get("role", "customer"), top_k=top_k)
    return {
        "allowed": True,
        "results": results,
        "instruction": "Use only these snippets for policy/process claims. Cite source_id/chunk_id. If evidence is insufficient, say so and offer ticket/escalation.",
    }


def get_customer_profile(customer_id: str, current_user: dict) -> dict:
    ok, reason = _allowed_customer_access(current_user, customer_id)
    if not ok:
        return {"allowed": False, "reason": reason}
    c = _find_customer(customer_id)
    if not c:
        return {"allowed": False, "reason": "Customer not found."}
    return {"allowed": True, "profile": _safe_customer_profile(c, current_user.get("role", "customer"))}


def get_customer_loans(customer_id: str, current_user: dict) -> dict:
    ok, reason = _allowed_customer_access(current_user, customer_id)
    if not ok:
        return {"allowed": False, "reason": reason}
    c = _find_customer(customer_id)
    if not c:
        return {"allowed": False, "reason": "Customer not found."}
    loans = []
    for loan in c.get("loans", []):
        loans.append({
            "loan_id": loan.get("loan_id"),
            "product": loan.get("product"),
            "asset": loan.get("vehicle") or loan.get("asset"),
            "principal": loan.get("principal"),
            "outstanding": loan.get("outstanding"),
            "emi": loan.get("emi"),
            "next_due_date": loan.get("next_due_date"),
            "tenure_months": loan.get("tenure_months"),
            "paid_emis": loan.get("paid_emis"),
            "remaining_emis": loan.get("remaining_emis"),
            "status": loan.get("status"),
            "dpd": loan.get("dpd", 0),
        })
    return {"allowed": True, "customer_id": c.get("customer_id"), "name": c.get("name"), "loans": loans}


def get_payment_history(customer_id: str, current_user: dict, limit: int = 5) -> dict:
    ok, reason = _allowed_customer_access(current_user, customer_id)
    if not ok:
        return {"allowed": False, "reason": reason}
    c = _find_customer(customer_id)
    if not c:
        return {"allowed": False, "reason": "Customer not found."}
    payments = sorted(c.get("payments", []), key=lambda p: p.get("date", ""), reverse=True)[: max(1, min(limit, 10))]
    return {"allowed": True, "customer_id": c.get("customer_id"), "payments": payments}


def _safe_loan_summary(loan: dict) -> dict:
    return {
        "loan_id": loan.get("loan_id"),
        "product": loan.get("product"),
        "asset": loan.get("vehicle") or loan.get("asset"),
        "principal": loan.get("principal"),
        "outstanding": loan.get("outstanding"),
        "emi": loan.get("emi"),
        "next_due_date": loan.get("next_due_date"),
        "tenure_months": loan.get("tenure_months"),
        "paid_emis": loan.get("paid_emis"),
        "remaining_emis": loan.get("remaining_emis"),
        "status": loan.get("status"),
        "dpd": loan.get("dpd", 0),
    }


def _safe_payment_summary(payment: dict) -> dict:
    return {
        "payment_id": payment.get("payment_id"),
        "loan_id": payment.get("loan_id"),
        "date": payment.get("date"),
        "amount": payment.get("amount"),
        "mode": payment.get("mode"),
        "status": payment.get("status"),
        "reference": payment.get("reference"),
        "note": payment.get("note"),
    }


def _employee_customer_summary(c: dict) -> dict:
    payments = sorted(
        c.get("payments", []),
        key=lambda p: p.get("date", ""),
        reverse=True,
    )[:5]

    return {
        "profile": _safe_customer_profile(c, "employee"),
        "loans": [_safe_loan_summary(loan) for loan in c.get("loans", [])],
        "recent_payments": [_safe_payment_summary(payment) for payment in payments],
        "documents": [
            {
                "doc_id": doc.get("doc_id"),
                "name": doc.get("name"),
                "loan_id": doc.get("loan_id"),
                "available": doc.get("available"),
            }
            for doc in c.get("documents", [])
        ],
    }


def search_customer_by_name(name: str, current_user: dict) -> dict:
    if current_user.get("role") != "employee":
        return {
            "allowed": False,
            "reason": "Only employee users can search customers by name.",
        }

    q = (name or "").lower().strip()

    if len(q) < 2:
        return {
            "allowed": False,
            "reason": "Please provide at least two characters of the customer name or a valid customer ID.",
        }

    matches = []

    for c in _customers():
        customer_id = c.get("customer_id", "").lower()
        customer_name = c.get("name", "").lower()

        if q in customer_name or q in customer_id:
            matches.append(_employee_customer_summary(c))

    return {
        "allowed": True,
        "matches": matches[:7],
        "instruction": (
            "Employee-safe lookup result. Use these matched records to answer the employee query. "
            "PII is already masked. You may summarize loan status, EMI, outstanding, DPD, recent payments, "
            "and document availability. If multiple customers match, ask the employee to choose one customer_id."
        ),
    }


def create_human_approval_request(action_type: str, reason: str, current_user: dict, customer_id: Optional[str] = None) -> dict:
    target_customer = customer_id or current_user.get("customer_id")
    if target_customer:
        ok, access_reason = _allowed_customer_access(current_user, target_customer)
        if not ok:
            return {"allowed": False, "reason": access_reason}
    req = {
        "approval_id": "APR-" + uuid.uuid4().hex[:8].upper(),
        "customer_id": target_customer,
        "requested_by": current_user["id"],
        "requested_by_role": current_user.get("role"),
        "action_type": redact_pii(action_type or "critical_action")[:120],
        "reason": redact_pii(reason or "Human approval required")[:1200],
        "status": "pending_human_approval",
        "created_at": int(time.time()),
    }
    append_json_list("approvals.json", req)
    return {
        "allowed": True,
        "human_approval_required": True,
        "approval": req,
        "instruction": "Tell the user this request has been routed for human approval. Do not promise approval or final financial/legal action.",
    }


def create_support_ticket(
    category: str,
    message: str,
    current_user: dict,
    customer_id: Optional[str] = None,
    user_explicitly_requested_ticket: bool = False,
) -> dict:
    if not user_explicitly_requested_ticket:
        return {
            "allowed": False,
            "reason": (
                "A support ticket should be created only when the user explicitly asks to create, raise, lodge, or open a ticket. "
                "For general advice or draft-response requests, answer with guidance instead of creating a ticket."
            ),
        }

    if looks_critical(category + " " + message):
        return create_human_approval_request(category, message, current_user, customer_id)

    target_customer = customer_id or current_user.get("customer_id")

    if target_customer:
        ok, reason = _allowed_customer_access(current_user, target_customer)

        if not ok:
            return {"allowed": False, "reason": reason}

    ticket = {
        "ticket_id": "TKT-" + uuid.uuid4().hex[:8].upper(),
        "customer_id": target_customer,
        "created_by": current_user["id"],
        "category": redact_pii(category or "general")[:120],
        "message": redact_pii(message or "")[:1000],
        "status": "open",
        "created_at": int(time.time()),
    }

    append_json_list("tickets.json", ticket)

    return {
        "allowed": True,
        "ticket": ticket,
        "instruction": "Tell the user the ticket was created. Do not promise resolution time unless retrieved policy explicitly says so.",
    }


def execute_tool(name: str, args: dict, current_user: dict) -> dict:
    if name == "search_knowledge_base":
        return search_knowledge_base(query=args.get("query", ""), current_user=current_user, top_k=int(args.get("top_k", 6)))
    if name == "get_customer_profile":
        return get_customer_profile(customer_id=args.get("customer_id", current_user.get("customer_id", "")), current_user=current_user)
    if name == "get_customer_loans":
        return get_customer_loans(customer_id=args.get("customer_id", current_user.get("customer_id", "")), current_user=current_user)
    if name == "get_payment_history":
        return get_payment_history(customer_id=args.get("customer_id", current_user.get("customer_id", "")), current_user=current_user, limit=int(args.get("limit", 5)))
    if name == "search_customer_by_name":
        return search_customer_by_name(name=args.get("name", ""), current_user=current_user)
    if name == "create_support_ticket":
        return create_support_ticket(
            category=args.get("category", "general"),
            message=args.get("message", ""),
            current_user=current_user,
            customer_id=args.get("customer_id"),
            user_explicitly_requested_ticket=bool(args.get("user_explicitly_requested_ticket", False)),
        )
    if name == "create_human_approval_request":
        return create_human_approval_request(action_type=args.get("action_type", "critical_action"), reason=args.get("reason", ""), current_user=current_user, customer_id=args.get("customer_id"))
    if name == "get_user_memory":
        return get_user_memory(current_user=current_user, limit=int(args.get("limit", 6)))
    if name == "save_conversation_memory":
        return save_conversation_memory(summary=args.get("summary", ""), current_user=current_user, kind=args.get("kind", "support_context"))
    return {"allowed": False, "reason": f"Unknown tool: {name}"}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Hybrid search + vector retrieval + reranking over read-only FinAssist policy/process KB chunks. Use for policy, process, portal, payment, NOC, foreclosure, privacy, and employee workflow questions.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 6}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "Fetch a masked customer profile by customer_id with role-based access control.",
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_loans",
            "description": "Fetch customer loan summary, EMI, outstanding amount, due date, DPD, and status. Use for account-specific loan or EMI questions.",
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment_history",
            "description": "Fetch recent payment records for the customer. Use for payment status, payment not reflected, receipt, debit, transaction, and reconciliation questions.",
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["customer_id"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_customer_by_name",
            "description": (
                "Employee-only customer lookup by customer name or customer ID. "
                "Use this FIRST when an employee asks to find/search/summarize a customer by name, "
                "for example Aarav, Priya, Rohan, or CUST001. "
                "Returns employee-safe masked profile, loan summaries, recent payments, and documents. "
                "Customer users must not use this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer name fragment or customer ID, for example Aarav, Priya, or CUST001.",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": (
                "Create a normal support ticket only when the user explicitly asks to create, raise, lodge, or open a ticket. "
                "Do not use this tool for 'what should I do', 'draft a response', 'explain process', or general guidance. "
                "For critical financial/legal actions, use create_human_approval_request instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "message": {"type": "string"},
                    "customer_id": {"type": "string"},
                    "user_explicitly_requested_ticket": {
                        "type": "boolean",
                        "description": "True only if the user explicitly asked to create/raise/lodge/open a support ticket.",
                    },
                },
                "required": ["category", "message", "user_explicitly_requested_ticket"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_human_approval_request",
            "description": "Create a pending human approval request for critical actions: refund, waiver, settlement, legal/repo/fraud issue, KYC/contact change, foreclosure quote, penalty reversal, or any binding financial/legal commitment.",
            "parameters": {
                "type": "object",
                "properties": {"action_type": {"type": "string"}, "reason": {"type": "string"}, "customer_id": {"type": "string"}},
                "required": ["action_type", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_memory",
            "description": "Fetch recent safe conversation memory for the logged-in user only.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 6}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_conversation_memory",
            "description": "Save a short safe support-context memory for this logged-in user only. Do not save secrets, OTPs, full PII, or another customer's details.",
            "parameters": {"type": "object", "properties": {"summary": {"type": "string"}, "kind": {"type": "string"}}, "required": ["summary"]},
        },
    },
]
