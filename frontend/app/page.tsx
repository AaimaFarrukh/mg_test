"use client";
import { FormEvent, useState } from "react";
import { ArrowRight, LockKeyhole, PackageCheck } from "lucide-react";
import { api } from "../lib/api";

export default function Login() {
  const [email, setEmail] = useState("erik@nordline.example");
  const [password, setPassword] = useState("Portal@2026");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError("");
    try {
      const data = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      localStorage.setItem("mg_token", data.access_token);
      localStorage.setItem("mg_role", data.role);
      window.location.href = data.role === "admin" ? "/admin" : "/orders";
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to sign in"); }
    finally { setLoading(false); }
  }
  return <main className="min-h-screen bg-slate-950">
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-10 lg:grid-cols-2">
      <section className="hidden text-white lg:block"><div className="mb-10 flex items-center gap-3"><span className="rounded-lg bg-teal-500 p-2"><PackageCheck /></span><span className="text-xl font-bold">MG Apparel</span></div><p className="mb-5 text-sm font-semibold uppercase tracking-[.25em] text-teal-300">Customer operations</p><h1 className="max-w-lg text-5xl font-semibold leading-tight">Your orders, moving forward.</h1><p className="mt-6 max-w-md text-lg text-slate-300">A secure workspace for shipment visibility, order support, and account updates.</p></section>
      <section className="card mx-auto w-full max-w-md p-8"><div className="mb-8 lg:hidden"><div className="flex items-center gap-3 font-bold"><span className="rounded-lg bg-teal-600 p-2 text-white"><PackageCheck /></span> MG Apparel</div></div><div className="mb-8"><h2 className="text-2xl font-bold">Welcome back</h2><p className="mt-2 text-sm text-slate-500">Sign in to access your order portal.</p></div><form onSubmit={submit} className="space-y-5"><label className="block text-sm font-medium">Email<input className="field mt-2" type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label><label className="block text-sm font-medium">Password<input className="field mt-2" type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-teal-700 py-3 font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60">{loading ? "Signing in..." : <>Sign in <ArrowRight size={17} /></>}</button></form><p className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-500"><LockKeyhole size={14} /> Your connection is protected</p></section>
    </div>
  </main>;
}

