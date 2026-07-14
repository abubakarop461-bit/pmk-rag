import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase-client";
import { User, Session } from "@supabase/supabase-js";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
      const dummyUser: any = {
        id: "00000000-0000-0000-0000-000000000001",
        email: "demo@local.dev",
        user_metadata: { name: "Demo User" }
      };
      const dummySession: any = {
        access_token: "demo_token",
        user: dummyUser
      };
      setSession(dummySession);
      setUser(dummyUser);
      setLoading(false);
      return;
    }

    // Get initial session on boot
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen to changes in auth state (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setUser(newSession?.user ?? null);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const logout = async () => {
    setLoading(true);
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
      setUser(null);
      setSession(null);
      setLoading(false);
      window.location.href = "/login";
      return;
    }
    await supabase.auth.signOut();
    setLoading(false);
  };

  return {
    user,
    session,
    loading,
    logout
  };
}
