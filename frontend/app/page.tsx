"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { 
  FolderPlus, 
  Trash2, 
  Briefcase, 
  LogOut, 
  Loader2,
  Plus,
  X,
  FileCode
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  description?: string;
  client_name?: string;
  project_number: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading, logout } = useAuth();
  
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal forms state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [projName, setProjName] = useState("");
  const [projNum, setProjNum] = useState("");
  const [clientName, setClientName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchProjects = async () => {
    setLoadingProjects(true);
    setError(null);
    try {
      const res = await apiClient.get("/projects");
      setProjects(res.data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to fetch project listings from server.");
    } finally {
      setLoadingProjects(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchProjects();
    }
  }, [user]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiClient.post("/projects", {
        name: projName,
        project_number: projNum,
        client_name: clientName || null,
        description: description || null,
        status: "active"
      });
      setShowCreateModal(false);
      // Reset
      setProjName("");
      setProjNum("");
      setClientName("");
      setDescription("");
      // Refresh
      fetchProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create construction project.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteProject = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete project '${name}'? This will delete all document records and files.`)) {
      return;
    }
    try {
      await apiClient.delete(`/projects/${id}`);
      fetchProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete project.");
    }
  };

  if (authLoading || (!user && authLoading)) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Header navbar */}
      <nav className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="h-6 w-6 text-blue-500" />
          <span className="text-xl font-bold tracking-tight text-white">Construction AI Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-400 font-medium">{user.email}</span>
          <button 
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 transition text-sm font-semibold"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </nav>

      {/* Main container */}
      <main className="max-w-6xl mx-auto px-6 py-10 flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">Projects</h1>
            <p className="mt-1 text-slate-400 text-sm">
              Manage your engineering contracts, specifications, drawings, and version chains.
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-semibold transition"
          >
            <Plus className="h-5 w-5" />
            New Project
          </button>
        </div>

        {/* Error notification */}
        {error && (
          <div className="bg-rose-950/50 border border-rose-800 rounded-lg p-4 text-sm text-rose-300">
            {error}
          </div>
        )}

        {/* Projects Grid */}
        {loadingProjects ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
          </div>
        ) : projects.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-xl p-16 text-center flex flex-col items-center gap-4">
            <Briefcase className="h-12 w-12 text-slate-600" />
            <div>
              <h3 className="text-lg font-bold text-white">No projects found</h3>
              <p className="text-slate-400 text-sm mt-1">Create your first construction project to begin uploading files.</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-white font-semibold transition"
            >
              Get Started
            </button>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((proj) => (
              <div 
                key={proj.id} 
                className="bg-slate-950 border border-slate-800 rounded-lg p-6 flex flex-col justify-between hover:border-slate-700 transition shadow-lg group relative"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300">
                      #{proj.project_number}
                    </span>
                    <button
                      onClick={() => handleDeleteProject(proj.id, proj.name)}
                      className="text-slate-600 hover:text-rose-500 transition opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <h3 className="text-xl font-bold mt-3 text-white truncate">{proj.name}</h3>
                  <p className="text-slate-400 text-sm mt-2 line-clamp-2">
                    {proj.description || "No project description provided."}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-900 flex items-center justify-between text-xs text-slate-400">
                  <span>Client: <b>{proj.client_name || "N/A"}</b></span>
                  <Link 
                    href={`/projects/${proj.id}`}
                    className="text-blue-400 hover:underline font-semibold flex items-center gap-1"
                  >
                    Open Documents
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Project Modal Dialog */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 max-w-md w-full shadow-2xl flex flex-col gap-6 relative">
            <button 
              onClick={() => setShowCreateModal(false)}
              className="absolute right-4 top-4 text-slate-500 hover:text-white transition"
            >
              <X className="h-5 w-5" />
            </button>
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <FolderPlus className="h-5 w-5 text-blue-500" />
                Create New Project
              </h3>
              <p className="text-sm text-slate-400 mt-1">Specify construction site details and tags.</p>
            </div>

            <form onSubmit={handleCreateProject} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-sm font-semibold text-slate-300">Project Name</label>
                <input
                  type="text"
                  required
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="e.g. Al Wasl Plaza Structural Refurbishment"
                  className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-semibold text-slate-300">Project Number</label>
                  <input
                    type="text"
                    required
                    value={projNum}
                    onChange={(e) => setProjNum(e.target.value)}
                    placeholder="e.g. CON-2026-04"
                    className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-semibold text-slate-300">Client Name</label>
                  <input
                    type="text"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g. Expo City Dubai"
                    className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-sm font-semibold text-slate-300">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Scope of works, main contractor terms, and locations..."
                  rows={3}
                  className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-2 py-2 rounded bg-blue-600 hover:bg-blue-500 transition text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : "Save Project"}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
