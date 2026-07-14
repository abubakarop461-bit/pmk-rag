"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase-client";
import { KeyRound, Mail, AlertCircle, Loader } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSignUp, setIsSignUp] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    // Redirect if already logged in
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.push("/");
      }
    });
  }, [router]);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMsg(null);

    try {
      if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        setMsg("Registration successful! Please check your email or log in.");
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        router.push("/");
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center font-sans px-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl flex flex-col gap-6 text-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white">AI Document Intelligence</h2>
            <p className="mt-2 text-xs text-blue-500 font-bold uppercase tracking-wider">Development Demo Mode</p>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Authentication is bypassed locally. Click the button below to immediately access the workspaces as a demo administrator.
          </p>
          <button
            onClick={() => {
              localStorage.setItem("supabase_session_token", "demo_token");
              router.push("/");
            }}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-bold transition shadow"
          >
            Enter Demo Workspace
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center font-sans px-4">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl flex flex-col gap-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold tracking-tight text-white">AI Document Intelligence</h2>
          <p className="mt-2 text-sm text-slate-400">
            {isSignUp ? "Create a platform account" : "Log in with your enterprise credentials"}
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-rose-950/50 border border-rose-800 rounded-lg p-3 text-sm text-rose-300">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {msg && (
          <div className="bg-emerald-950/50 border border-emerald-800 rounded-lg p-3 text-sm text-emerald-300">
            <span>{msg}</span>
          </div>
        )}

        <form onSubmit={handleAuth} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-slate-300">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@company.com"
                className="w-full pl-10 pr-4 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-slate-300">Password</label>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2 rounded bg-blue-600 hover:bg-blue-500 transition text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader className="h-5 w-5 animate-spin" /> : isSignUp ? "Sign Up" : "Log In"}
          </button>
        </form>

        <div className="text-center text-sm text-slate-400">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError(null);
              setMsg(null);
            }}
            className="hover:underline text-blue-400 font-medium"
          >
            {isSignUp ? "Already have an account? Log in" : "Need an account? Sign up"}
          </button>
        </div>
      </div>
    </div>
  );
}
