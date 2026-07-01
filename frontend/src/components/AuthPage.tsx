import { useState } from "react";
import type { FormEvent } from "react";
import { Bot, LockKeyhole, Sparkles } from "lucide-react";
import { login, setToken, signup } from "../api";
import type { User } from "../types";

export default function AuthPage({ onAuth }: { onAuth: (user: User) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("aarav@example.com");
  const [password, setPassword] = useState("Customer@123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res =
        mode === "login"
          ? await login(email, password)
          : await signup(name, email, password);
      setToken(res.token);
      onAuth(res.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  function useDemo(type: "customer" | "employee") {
    if (type === "customer") {
      setEmail("aarav@example.com");
      setPassword("Customer@123");
    } else {
      setEmail("meera.employee@finassist.local");
      setPassword("Employee@123");
    }
    setMode("login");
  }

  return (
    <main className="relative min-h-screen overflow-y-auto bg-slate-950 text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,#2563eb55,transparent_34%),radial-gradient(circle_at_bottom_right,#f9731655,transparent_30%)]" />
      <section className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-4 py-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-slate-200">
            <Sparkles size={16} /> AI-powered support platform
          </div>
          <h1 className="max-w-3xl text-4xl font-black leading-tight tracking-tight sm:text-6xl">
            FinAssist AI
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
            Access trusted answers for EMI, payments, NOC, loan records, and
            support workflows through a secure assistant with verified
            knowledge, role-based access, and human review for sensitive
            actions.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              "Verified policy answers",
              "Role-based access",
              "Human approval workflows",
            ].map((item) => (
              <div
                key={item}
                className="rounded-2xl border border-white/10 bg-white/10 p-4 text-sm font-semibold text-slate-200"
              >
                {item}
              </div>
            ))}
          </div>
        </div>

        <form
          onSubmit={submit}
          className="glass rounded-[2rem] border border-white/20 p-6 text-slate-950 shadow-soft sm:p-8"
        >
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-950 text-white">
                <Bot size={22} />
              </div>
              <div>
                <h2 className="text-xl font-black">Secure Login</h2>
                <p className="text-sm text-slate-500">
                  Customer and employee access
                </p>
              </div>
            </div>
            <LockKeyhole className="text-slate-400" />
          </div>

          <div className="mb-5 grid grid-cols-2 rounded-2xl bg-slate-100 p-1 text-sm font-bold">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`rounded-xl px-4 py-2 ${mode === "login" ? "bg-white shadow-sm" : "text-slate-500"}`}
            >
              Login
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`rounded-xl px-4 py-2 ${mode === "signup" ? "bg-white shadow-sm" : "text-slate-500"}`}
            >
              Signup
            </button>
          </div>

          {mode === "signup" && (
            <label className="mb-4 block text-sm font-bold">
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-500"
                placeholder="Your name"
              />
            </label>
          )}
          <label className="mb-4 block text-sm font-bold">
            Email
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-500"
              placeholder="name@example.com"
            />
          </label>
          <label className="mb-4 block text-sm font-bold">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-500"
              placeholder="••••••••"
            />
          </label>

          {error && (
            <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
              {error}
            </p>
          )}

          <button
            disabled={loading}
            className="w-full rounded-2xl bg-slate-950 px-5 py-3 font-black text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Continue"
                : "Create account"}
          </button>

          <div className="mt-5 grid gap-3 text-xs font-bold sm:grid-cols-2">
            <button
              type="button"
              onClick={() => useDemo("customer")}
              className="rounded-2xl border border-slate-200 px-3 py-3 text-slate-600 hover:bg-slate-50"
            >
              Use customer demo
            </button>
            <button
              type="button"
              onClick={() => useDemo("employee")}
              className="rounded-2xl border border-slate-200 px-3 py-3 text-slate-600 hover:bg-slate-50"
            >
              Use employee demo
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
