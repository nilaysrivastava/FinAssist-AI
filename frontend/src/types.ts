export type Role = "customer" | "employee";

export type User = {
  id: string;
  name: string;
  email: string;
  role: Role;
  customer_id?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  tool_trace?: ToolTrace[];
  blocked?: boolean;
  needs_human_approval?: boolean;
  email_offer?: EmailOffer | null;
};

export type Source = {
  id: string;
  chunk_id?: string | null;
  title: string;
  category: string;
  section?: string | null;
  citation?: string | null;
  score?: number | null;
};

export type ToolTrace = {
  tool: string;
  allowed: boolean;
  reason?: string | null;
  human_approval_required?: boolean;
};

export type EmailOffer = {
  offer_id: string;
  title: string;
  message: string;
  recipient_masked: string;
};
