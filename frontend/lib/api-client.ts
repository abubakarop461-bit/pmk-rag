import axios from "axios";
import { supabase } from "./supabase-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor to attach the Supabase JWT token automatically to every request
apiClient.interceptors.request.use(
  async (config) => {
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
      config.headers.Authorization = "Bearer demo_token";
      return config;
    }
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
