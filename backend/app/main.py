import time
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.auth import create_user, current_user, find_user_by_email, issue_token, public_user, verify_password
from app.config import FRONTEND_ORIGIN
from app.guardrails import ai_guardrail_decision
from app.ingest import ensure_index_exists
from app.llm import run_chat
from app.memory import auto_memory_note
from app.models import AuthResponse, ChatRequest, ChatResponse, LoginRequest, SignupRequest, TicketRequest, UserOut, SendEmailRequest, SendEmailResponse
from app.security import redact_pii
from app.storage import append_json_list, read_json
from app.tools import create_human_approval_request, create_support_ticket
from app.email_service import create_email_offer, send_email_offer

app = FastAPI(title="FinAssist GenAI Chatbot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    ensure_index_exists()

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "FinAssist AI backend is running",
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/api/health")
def health():
    return {"ok": True, "service": "finassist-genai-chatbot", "version": "2.0.0"}


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    user = create_user(payload.name, payload.email, payload.password)
    return {"token": issue_token(user), "user": public_user(user)}


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = find_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["salt"], user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": issue_token(user), "user": public_user(user)}


@app.get("/api/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return user


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: dict = Depends(current_user)):
    history = [m.model_dump() for m in payload.history]
    decision = ai_guardrail_decision(payload.message, user, history)
    action = decision.get("action")
    message = decision.get("message") or ""

    if action == "refuse":
        answer = message or "I can’t help with that request."

        append_json_list(
            "chat_logs.json",
            {
                "user_id": user["id"],
                "customer_id": user.get("customer_id"),
                "message": redact_pii(payload.message),
                "answer": redact_pii(answer),
                "blocked": True,
                "needs_human_approval": False,
                "created_at": int(time.time()),
            },
        )

        return {
            "answer": answer,
            "sources": [],
            "tool_trace": [],
            "blocked": True,
            "needs_human_approval": False,
            "email_offer": None,
        }

    if action == "clarify":
        answer = message or "Could you clarify your FinAssist support request?"

        append_json_list(
            "chat_logs.json",
            {
                "user_id": user["id"],
                "customer_id": user.get("customer_id"),
                "message": redact_pii(payload.message),
                "answer": redact_pii(answer),
                "blocked": False,
                "needs_human_approval": False,
                "created_at": int(time.time()),
            },
        )

        return {
            "answer": answer,
            "sources": [],
            "tool_trace": [],
            "blocked": False,
            "needs_human_approval": False,
            "email_offer": None,
        }

    if action == "chitchat":
        answer = message or "Hello! I can help you with loan details, EMI status, payment issues, NOC, documents, policies, or support tickets."

        append_json_list(
            "chat_logs.json",
            {
                "user_id": user["id"],
                "customer_id": user.get("customer_id"),
                "message": redact_pii(payload.message),
                "answer": redact_pii(answer),
                "blocked": False,
                "needs_human_approval": False,
                "email_offer_id": None,
                "created_at": int(time.time()),
            },
        )

        return {
            "answer": answer,
            "sources": [],
            "tool_trace": [],
            "blocked": False,
            "needs_human_approval": False,
            "email_offer": None,
        }


    if action == "human_approval":
        approval_result = create_human_approval_request(
            action_type="critical_request",
            reason=payload.message,
            current_user=user,
            customer_id=user.get("customer_id"),
        )

        answer = (
            "This request requires human review before any action can be taken. "
            "I have routed it for approval and the support team will review it."
        )

        tool_trace = [
            {
                "tool": "create_human_approval_request",
                "allowed": approval_result.get("allowed", True),
                "reason": approval_result.get("reason"),
                "human_approval_required": True,
            }
        ]

        email_offer = create_email_offer(
            message=payload.message,
            answer=answer,
            current_user=user,
            sources=[],
            tool_trace=tool_trace,
            blocked=False,
            needs_human_approval=True,
        )

        append_json_list(
            "chat_logs.json",
            {
                "user_id": user["id"],
                "customer_id": user.get("customer_id"),
                "message": redact_pii(payload.message),
                "answer": redact_pii(answer),
                "blocked": False,
                "needs_human_approval": True,
                "created_at": int(time.time()),
            },
        )

        auto_memory_note(payload.message, answer, user)

        return {
            "answer": answer,
            "sources": [],
            "tool_trace": tool_trace,
            "blocked": False,
            "needs_human_approval": True,
            "email_offer": email_offer,
        }

    answer, sources, tool_trace, needs_human_approval = run_chat(payload.message, history, user)

    email_offer = create_email_offer(
        message=payload.message,
        answer=answer,
        current_user=user,
        sources=sources,
        tool_trace=tool_trace,
        blocked=False,
        needs_human_approval=needs_human_approval,
    )

    append_json_list(
        "chat_logs.json",
        {
            "user_id": user["id"],
            "customer_id": user.get("customer_id"),
            "message": redact_pii(payload.message),
            "answer": redact_pii(answer),
            "blocked": False,
            "needs_human_approval": bool(needs_human_approval),
            "email_offer_id": email_offer.get("offer_id") if email_offer else None,
            "created_at": int(time.time()),
        },
    )

    auto_memory_note(payload.message, answer, user)

    return {
        "answer": answer,
        "sources": sources,
        "tool_trace": tool_trace,
        "blocked": False,
        "needs_human_approval": bool(needs_human_approval),
        "email_offer": email_offer,
    }


@app.post("/api/email/send-offer", response_model=SendEmailResponse)
def send_email_summary(payload: SendEmailRequest, user: dict = Depends(current_user)):
    result = send_email_offer(payload.offer_id, user)

    if not result.get("allowed"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Unable to send email."))

    return {
        "allowed": True,
        "message": result.get("message", "Email sent."),
        "email_id": result.get("email_id"),
        "recipient_masked": result.get("recipient_masked"),
    }


@app.get("/api/debug/customers")
def debug_customers(user: dict = Depends(current_user)):
    if user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Employee access required")
    return read_json("customers.json", [])


@app.post("/api/tickets")
def create_ticket(payload: TicketRequest, user: dict = Depends(current_user)):
    return create_support_ticket(payload.category, payload.message, user)
