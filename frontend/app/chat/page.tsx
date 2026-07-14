"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Loader2,
  Sparkles,
  Award,
  Layers,
  Clock,
  BookOpen,
  ArrowLeft,
  XCircle,
  StopCircle,
  FileText,
  HelpCircle,
  ShieldAlert
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  project_number: string;
}

interface ChatSession {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
}

interface Citation {
  document_id: string;
  filename: string;
  pages: number[];
  document_type: string;
}

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at?: string;
  timings?: {
    retrieval_ms: number;
    prompt_construction_ms: number;
    generation_ms: number;
    total_ms: number;
  };
}

function ChatContent() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const projectIdParam = searchParams ? searchParams.get("project_id") : null;

  // Project and Sessions selection states
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Chat message flows
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [streamingMessage, setStreamingMessage] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streamingConfidence, setStreamingConfidence] = useState("");
  const [streamingTimings, setStreamingTimings] = useState<any>(null);
  
  // Loading & Action states
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Rename session title states & handlers
  const [editingTitle, setEditingTitle] = useState(false);
  const [newTitleVal, setNewTitleVal] = useState("");

  const handleStartRename = () => {
    const activeSession = sessions.find((s) => s.id === activeSessionId);
    if (activeSession) {
      setNewTitleVal(activeSession.title);
      setEditingTitle(true);
    }
  };

  const handleSaveRename = async () => {
    if (!activeSessionId || !newTitleVal.trim()) return;
    try {
      const res = await apiClient.patch<ChatSession>(`/chat/session/${activeSessionId}/title?title=${encodeURIComponent(newTitleVal)}`);
      setSessions(sessions.map((s) => s.id === activeSessionId ? { ...s, title: res.data.title } : s));
      setEditingTitle(false);
    } catch (err) {
      console.error("Failed to rename session thread title", err);
    }
  };

  // Load projects
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }

    async function loadProjects() {
      try {
        const res = await apiClient.get<Project[]>("/projects");
        const data = res.data;
        setProjects(data);
        if (data.length > 0) {
          const targetProj = projectIdParam && data.some(p => p.id === projectIdParam)
            ? projectIdParam
            : data[0].id;
          setSelectedProject(targetProj);
        }
      } catch (err) {
        console.error("Failed to load projects", err);
      } finally {
        setLoadingProjects(false);
      }
    }
    loadProjects();
  }, [user, authLoading]);

  // Load chat sessions when active project changes
  useEffect(() => {
    if (!selectedProject) return;
    loadSessions();
  }, [selectedProject]);

  // Load history when active session changes
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }
    loadHistory();
  }, [activeSessionId]);

  // Scroll to bottom on updates
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  async function loadSessions() {
    setLoadingSessions(true);
    try {
      const res = await apiClient.get<ChatSession[]>(`/chat/sessions?project_id=${selectedProject}`);
      const data = res.data;
      setSessions(data);
      if (data.length > 0) {
        setActiveSessionId(data[0].id);
      } else {
        setActiveSessionId(null);
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    } finally {
      setLoadingSessions(false);
    }
  }

  async function loadHistory() {
    if (!activeSessionId) return;
    setLoadingHistory(true);
    try {
      const res = await apiClient.get<Message[]>(`/chat/session/${activeSessionId}/history`);
      setMessages(res.data);
    } catch (err) {
      console.error("Failed to load chat history", err);
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleCreateSession() {
    if (!selectedProject) return;
    const title = `Thread #${sessions.length + 1}`;
    try {
      const res = await apiClient.post<ChatSession>("/chat/session", {
        project_id: selectedProject,
        title
      });
      const session = res.data;
      setSessions([session, ...sessions]);
      setActiveSessionId(session.id);
    } catch (err) {
      console.error("Failed to create chat session", err);
    }
  }

  async function handleDeleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat thread?")) return;
    try {
      await apiClient.delete(`/chat/session/${id}`);
      setSessions(sessions.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(sessions.length > 1 ? sessions.find((s) => s.id !== id)?.id || null : null);
      }
    } catch (err) {
      console.error("Failed to delete chat session", err);
    }
  }

  // Handle SSE streaming completion
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !activeSessionId || generating) return;

    const userMessageText = query;
    setQuery("");
    
    // Add user message immediately to the view
    const userMsg: Message = { role: "user", content: userMessageText };
    setMessages((prev) => [...prev, userMsg]);
    
    setGenerating(true);
    setStreamingMessage("");
    setStreamingCitations([]);
    setStreamingConfidence("");
    setStreamingTimings(null);

    // Get Auth credentials token from local supabase mappings
    // Fallback URL resolving
    let token = localStorage.getItem("supabase_session_token") || "";
    if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
      token = "demo_token";
    }
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`${backendUrl}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          query: userMessageText,
          session_id: activeSessionId,
          project_id: selectedProject
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Chat request failed: ${response.status} - ${errorText}`);
      }

      if (!response.body) {
        throw new Error("Empty streaming response body.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || ""; // retain incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          if (line.startsWith("data: ")) {
            const rawData = line.substring(6).trim();
            if (rawData === "[DONE]") {
              break;
            }
            try {
              const parsed = JSON.parse(rawData);
              if (parsed.token) {
                setStreamingMessage((prev) => prev + parsed.token);
              } else if (parsed.validated_content) {
                // If answer validation fails post-generation, replace message with fallback string
                setStreamingMessage(parsed.validated_content);
              } else if (parsed.citations) {
                setStreamingCitations(parsed.citations);
                setStreamingConfidence(parsed.confidence_summary);
                setStreamingTimings(parsed.timings);
              } else if (parsed.error) {
                setStreamingMessage((prev) => prev + `\n\n[Error: ${parsed.error}]`);
              }
            } catch (err) {
              console.error("Failed to parse SSE payload", err);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Generation aborted by user.");
      } else {
        console.error("RAG stream query failed:", err);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `⚠️ Error: ${err.message || "Failed to retrieve streaming response."}` }
        ]);
      }
    } finally {
      setGenerating(false);
      abortControllerRef.current = null;
      // Reload conversation history & sessions list to update generated titles
      loadHistory();
      loadSessions();
    }
  }

  // Cancel generation
  function handleCancelGeneration() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setGenerating(false);
      setStreamingMessage((prev) => prev + "\n\n*[Response generation cancelled by user]*");
    }
  }

  if (loadingProjects) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-white">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      
      {/* Sidebar - Threads switcher */}
      <aside className="w-80 border-r border-slate-900 bg-slate-950 flex flex-col">
        {/* Project Selector header */}
        <div className="p-4 border-b border-slate-900 flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <Layers className="h-3.5 w-3.5 text-blue-500" />
            Active Project Scope
          </div>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.project_number})
              </option>
            ))}
          </select>
        </div>

        {/* Start Chat Button */}
        <div className="p-4">
          <button
            onClick={handleCreateSession}
            disabled={!selectedProject}
            className="w-full py-2 bg-slate-900 hover:bg-slate-850 text-white border border-slate-800 rounded font-semibold text-sm transition flex items-center justify-center gap-2"
          >
            <Plus className="h-4 w-4 text-blue-400" />
            New Chat Thread
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
          <div className="px-2 py-1 text-[10px] font-bold text-slate-600 uppercase tracking-wider">
            Conversations Threads
          </div>
          {loadingSessions ? (
            <div className="flex justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-600 font-medium">
              No chat sessions. Start a new thread above.
            </div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`w-full text-left px-3 py-2.5 rounded text-sm transition flex items-center justify-between group ${
                  activeSessionId === s.id
                    ? "bg-blue-950/40 text-blue-300 border border-blue-900/60"
                    : "hover:bg-slate-900/50 text-slate-400 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">{s.title}</span>
                </div>
                <Trash2
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  className="h-4 w-4 text-slate-600 hover:text-rose-500 opacity-0 group-hover:opacity-100 transition flex-shrink-0"
                />
              </button>
            ))
          )}
        </div>

        {/* Back Link */}
        <div className="p-4 border-t border-slate-900">
          <Link
            href={selectedProject ? `/projects/${selectedProject}` : "/"}
            className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Project Details
          </Link>
        </div>
      </aside>

      {/* Main Chat Screen Area */}
      <main className="flex-1 flex flex-col bg-slate-950">
        
        {/* Top Active Session Dashboard */}
        <header className="px-6 py-4 border-b border-slate-900 flex items-center justify-between bg-slate-950/60 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-blue-400 animate-pulse" />
            <div>
              {editingTitle ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={newTitleVal}
                    onChange={(e) => setNewTitleVal(e.target.value)}
                    className="px-2.5 py-1 text-sm bg-slate-900 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-blue-500"
                    onKeyDown={(e) => e.key === "Enter" && handleSaveRename()}
                    autoFocus
                  />
                  <button onClick={handleSaveRename} className="text-xs bg-blue-600 hover:bg-blue-500 px-2 py-1 rounded text-white font-bold transition">
                    Save
                  </button>
                  <button onClick={() => setEditingTitle(false)} className="text-xs bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded text-slate-400 transition">
                    Cancel
                  </button>
                </div>
              ) : (
                <h2 className="text-sm font-bold text-white flex items-center gap-2 group cursor-pointer" onClick={handleStartRename}>
                  {sessions.find((s) => s.id === activeSessionId)?.title || "Select or start a chat session"}
                  <span className="text-[10px] text-slate-500 hover:text-slate-300 font-normal opacity-0 group-hover:opacity-100 transition">
                    (click to rename)
                  </span>
                </h2>
              )}
              <p className="text-[10px] text-slate-500 font-semibold mt-0.5 uppercase tracking-wider">
                {projects.find((p) => p.id === selectedProject)?.name || "Global Scope"} RAG Layer
              </p>
            </div>
          </div>
          
          {/* Confidence Badge Display */}
          {(streamingConfidence || messages.length > 0) && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500 font-bold uppercase">Retrieval Confidence:</span>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                (streamingConfidence || "High") === "Very High" || (streamingConfidence || "High") === "High"
                  ? "bg-emerald-950 text-emerald-400 border-emerald-900"
                  : (streamingConfidence || "High") === "Medium"
                  ? "bg-amber-950 text-amber-400 border-amber-900"
                  : "bg-rose-950 text-rose-400 border-rose-900"
              }`}>
                <Award className="h-3 w-3" />
                {streamingConfidence || "High"}
              </span>
            </div>
          )}
        </header>

        {/* Message scroll container */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
          {loadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : !activeSessionId ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-3 max-w-md mx-auto">
              <MessageSquare className="h-12 w-12 text-slate-800" />
              <h3 className="text-lg font-bold text-slate-400">RAG Chat System</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Select an existing conversation thread from the left menu or create a new session thread to begin query testing.
              </p>
            </div>
          ) : messages.length === 0 && !streamingMessage ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4 max-w-lg mx-auto bg-slate-950">
              <div className="p-4 bg-slate-900 border border-slate-800 rounded-full text-blue-500">
                <Sparkles className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-md font-bold text-white">Ask your project documents anything</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm leading-relaxed">
                  Enter questions about concrete specifications, drawing column grids, or contract liability constraints.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6 max-w-4xl mx-auto">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {/* Assistant Icon */}
                  {msg.role === "assistant" && (
                    <div className="h-8 w-8 rounded bg-blue-900/60 border border-blue-800 flex items-center justify-center text-blue-300 flex-shrink-0 mt-0.5">
                      <Sparkles className="h-4 w-4" />
                    </div>
                  )}

                  {/* Message Card bubble */}
                  <div className={`max-w-2xl px-5 py-3.5 rounded-xl shadow-md border ${
                    msg.role === "user"
                      ? "bg-slate-900 border-slate-800 text-slate-200"
                      : "bg-slate-950 border-slate-900 text-slate-300"
                  }`}>
                    {/* Message content */}
                    <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
                      {msg.content}
                    </div>

                    {/* Citations Footer */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-900/50 flex flex-col gap-2">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                          <BookOpen className="h-3.5 w-3.5 text-blue-400" />
                          Context Sources Citations ({msg.citations.length})
                        </div>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {msg.citations.map((cit, cIdx) => (
                            <div
                              key={cIdx}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800/80 text-[10px] font-mono text-slate-300"
                            >
                              <FileText className="h-3 w-3 text-slate-400" />
                              <span>{cit.filename}</span>
                              <span className="text-slate-600">|</span>
                              <span>Pages {cit.pages.join(", ")}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* User Icon */}
                  {msg.role === "user" && (
                    <div className="h-8 w-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 flex-shrink-0 mt-0.5">
                      <FileText className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}

              {/* Streaming active message */}
              {streamingMessage && (
                <div className="flex gap-4 justify-start">
                  <div className="h-8 w-8 rounded bg-blue-900/60 border border-blue-800 flex items-center justify-center text-blue-300 flex-shrink-0 mt-0.5">
                    <Sparkles className="h-4 w-4 animate-spin" />
                  </div>
                  
                  <div className="max-w-2xl px-5 py-3.5 rounded-xl bg-slate-950 border border-slate-900 text-slate-300 shadow-md">
                    <div className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
                      {streamingMessage}
                    </div>

                    {/* Citations Footer */}
                    {streamingCitations.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-slate-900/50 flex flex-col gap-2">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                          <BookOpen className="h-3.5 w-3.5 text-blue-400" />
                          Context Sources Citations ({streamingCitations.length})
                        </div>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {streamingCitations.map((cit, cIdx) => (
                            <div
                              key={cIdx}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800/80 text-[10px] font-mono text-slate-300"
                            >
                              <FileText className="h-3 w-3 text-slate-400" />
                              <span>{cit.filename}</span>
                              <span className="text-slate-600">|</span>
                              <span>Pages {cit.pages.join(", ")}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Timing metrics bar on completed stream */}
              {streamingTimings && (
                <div className="flex items-center justify-between text-[10px] text-slate-500 bg-slate-900/30 border border-slate-900/60 px-4 py-2 rounded-lg font-mono max-w-4xl mx-auto gap-4 flex-wrap">
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-slate-400" />
                    <span>RAG Latency Milestones:</span>
                  </div>
                  <div className="flex items-center gap-4 flex-wrap">
                    <span>Retr: {streamingTimings.retrieval_ms}ms</span>
                    <span>Prompt: {streamingTimings.prompt_construction_ms}ms</span>
                    <span>Gen: {streamingTimings.generation_ms}ms</span>
                    <span className="text-blue-400 font-bold">Total: {streamingTimings.total_ms}ms</span>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>
          )}
        </div>

        {/* Input Bar Form */}
        {activeSessionId && (
          <div className="p-6 border-t border-slate-900 bg-slate-950/80 backdrop-blur-md">
            <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={generating}
                placeholder="Ask a question about project documents..."
                className="flex-1 px-4 py-3 rounded-lg bg-slate-900 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
              />
              
              {generating ? (
                <button
                  type="button"
                  onClick={handleCancelGeneration}
                  className="px-4 py-3 bg-rose-600 hover:bg-rose-500 text-white rounded-lg transition flex items-center justify-center gap-1.5 text-sm font-semibold"
                >
                  <StopCircle className="h-4 w-4" />
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!query.trim() || generating}
                  className="px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-1.5 text-sm font-semibold"
                >
                  <Send className="h-4 w-4" />
                  Send
                </button>
              )}
            </form>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
