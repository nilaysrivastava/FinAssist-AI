from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["customer", "employee"]
    customer_id: Optional[str] = None


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []


class Source(BaseModel):
    id: Optional[str] = None
    chunk_id: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None
    section: Optional[str] = None
    citation: Optional[str] = None
    score: Optional[float] = None


class ToolTrace(BaseModel):
    tool: str
    allowed: bool = True
    reason: Optional[str] = None
    human_approval_required: bool = False


class EmailOffer(BaseModel):
    offer_id: str
    title: str
    message: str
    recipient_masked: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source] = []
    tool_trace: List[ToolTrace] = []
    blocked: bool = False
    needs_human_approval: bool = False
    email_offer: Optional[EmailOffer] = None


class TicketRequest(BaseModel):
    category: str
    message: str
    customer_id: Optional[str] = None


class SendEmailRequest(BaseModel):
    offer_id: str


class SendEmailResponse(BaseModel):
    allowed: bool
    message: str
    email_id: Optional[str] = None
    recipient_masked: Optional[str] = None