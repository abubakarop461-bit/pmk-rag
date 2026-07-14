"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import {
  Settings,
  Cloud,
  FolderOpen,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Database,
  ArrowLeft,
  ChevronRight,
  AlertTriangle,
  Play,
  FileText
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  project_number: string;
}

interface ConnectorAccount {
  id: string;
  project_id: string;
  provider: string;
  account_email: string;
  status: string;
  created_at: string;
}

interface CloudFolder {
  id: string;
  name: string;
}

interface SyncJob {
  id: string;
  account_id: string;
  status: string;
  started_at: string;
  finished_at?: string;
  files_added: number;
  files_updated: number;
  files_deleted: number;
  error_message?: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Project selector
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  
  // Connector accounts listing
  const [accounts, setAccounts] = useState<ConnectorAccount[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [activeAccount, setActiveAccount] = useState<ConnectorAccount | null>(null);

  // Folders and sync mapping state
  const [cloudFolders, setCloudFolders] = useState<CloudFolder[]>([]);
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [selectedFolderId, setSelectedFolderId] = useState("");
  
  // Sync history and jobs state
  const [syncJobs, setSyncJobs] = useState<SyncJob[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [syncingFolderId, setSyncingFolderId] = useState<string | null>(null);

  // OAuth Simulated Auth Codes
  const [authEmail, setAuthEmail] = useState("");
  const [authCode, setAuthCode] = useState("mock_code");
  const [loadingConnect, setLoadingConnect] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    loadProjects();
  }, [user, authLoading]);

  // Reload accounts when project selection changes
  useEffect(() => {
    if (!selectedProject) return;
    loadAccounts();
  }, [selectedProject]);

  // Reload folders and sync history when active account changes
  useEffect(() => {
    if (!activeAccount) {
      setCloudFolders([]);
      setSyncJobs([]);
      return;
    }
    loadFolders();
    loadSyncHistory();
  }, [activeAccount]);

  async function loadProjects() {
    try {
      const res = await apiClient.get<Project[]>("/api/projects");
      setProjects(res.data);
      if (res.data.length > 0) {
        setSelectedProject(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load projects", err);
    }
  }

  async function loadAccounts() {
    setLoadingAccounts(true);
    try {
      const res = await apiClient.get<ConnectorAccount[]>(`/api/connectors/accounts?project_id=${selectedProject}`);
      setAccounts(res.data);
      if (res.data.length > 0) {
        setActiveAccount(res.data[0]);
      } else {
        setActiveAccount(null);
      }
    } catch (err) {
      console.error("Failed to load connector accounts", err);
    } finally {
      setLoadingAccounts(false);
    }
  }

  async function loadFolders() {
    if (!activeAccount) return;
    setLoadingFolders(true);
    try {
      const res = await apiClient.get<CloudFolder[]>(`/api/connectors/folders/list?account_id=${activeAccount.id}`);
      setCloudFolders(res.data);
      if (res.data.length > 0) {
        setSelectedFolderId(res.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load folders tree", err);
    } finally {
      setLoadingFolders(false);
    }
  }

  async function loadSyncHistory() {
    if (!activeAccount) return;
    setLoadingJobs(true);
    try {
      const res = await apiClient.get<SyncJob[]>(`/api/connectors/sync/jobs?account_id=${activeAccount.id}`);
      setSyncJobs(res.data);
    } catch (err) {
      console.error("Failed to load sync jobs history", err);
    } finally {
      setLoadingJobs(false);
    }
  }

  async function handleConnectAccount(provider: string) {
    if (!selectedProject || !authEmail.trim()) {
      alert("Please provide account email address.");
      return;
    }
    setLoadingConnect(true);
    try {
      await apiClient.post("/api/connectors/connect", {
        project_id: selectedProject,
        provider,
        auth_code: authCode,
        account_email: authEmail
      });
      setAuthEmail("");
      loadAccounts();
    } catch (err) {
      console.error("Failed to connect account", err);
      alert("OAuth connection failed. Verify permissions or settings.");
    } finally {
      setLoadingConnect(false);
    }
  }

  async function handleConfigureSync() {
    if (!activeAccount || !selectedFolderId) return;
    const folderName = cloudFolders.find((f) => f.id === selectedFolderId)?.name || "Selected Cloud Directory";
    try {
      const configuredFolder = await apiClient.post("/api/connectors/folders/configure", {
        account_id: activeAccount.id,
        folder_id: selectedFolderId,
        folder_name: folderName
      });
      alert(`Synchronizer folder '${folderName}' bound successfully!`);
      
      // Trigger a manual sync right away on configuration
      handleTriggerSync(configuredFolder.data.id);
    } catch (err) {
      console.error("Failed to configure folder", err);
    }
  }

  async function handleTriggerSync(folderRowId: string) {
    setSyncingFolderId(folderRowId);
    try {
      await apiClient.post(`/api/connectors/sync/manual?folder_id=${folderRowId}`);
      // Polling refresh in 3 seconds to check job updates
      setTimeout(() => {
        loadSyncHistory();
        setSyncingFolderId(null);
      }, 3000);
    } catch (err) {
      console.error("Failed to manual sync", err);
      setSyncingFolderId(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      
      {/* Top Header */}
      <header className="px-8 py-5 border-b border-slate-900 bg-slate-950 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="h-6 w-6 text-blue-500 animate-spin-slow" />
          <div>
            <h1 className="text-lg font-bold text-white">System Integrations</h1>
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mt-0.5">Cloud Connectors & Incremental Sync</p>
          </div>
        </div>
        <Link
          href={selectedProject ? `/projects/${selectedProject}` : "/"}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs font-bold text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
      </header>

      {/* Main Body Columns */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-8 py-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Column - Scope & Connections Setup */}
        <div className="space-y-6">
          
          {/* Project Scope Card */}
          <div className="p-5 bg-slate-950 border border-slate-900 rounded-xl shadow-md space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
              <Database className="h-4 w-4 text-blue-500" />
              1. Selected Project Scope
            </div>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-900 border border-slate-800 rounded text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.project_number})
                </option>
              ))}
            </select>
          </div>

          {/* Add Integrations Card */}
          <div className="p-5 bg-slate-950 border border-slate-900 rounded-xl shadow-md space-y-4">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
              <Cloud className="h-4 w-4 text-blue-500" />
              2. Add Cloud Provider Connection
            </div>
            
            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-500">Account Owner Email Address</label>
              <input
                type="email"
                placeholder="e.g. engineer@pmk-rag.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="grid grid-cols-1 gap-2 pt-2">
              <button
                onClick={() => handleConnectAccount("google_drive")}
                disabled={loadingConnect}
                className="py-2.5 bg-slate-900 hover:bg-slate-850 text-white rounded text-xs font-bold border border-slate-800 transition flex items-center justify-center gap-2"
              >
                {loadingConnect ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Connect Google Drive"}
              </button>
              <button
                onClick={() => handleConnectAccount("sharepoint")}
                disabled={loadingConnect}
                className="py-2.5 bg-slate-900 hover:bg-slate-850 text-white rounded text-xs font-bold border border-slate-800 transition flex items-center justify-center gap-2"
              >
                {loadingConnect ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Connect SharePoint"}
              </button>
              <button
                onClick={() => handleConnectAccount("onedrive")}
                disabled={loadingConnect}
                className="py-2.5 bg-slate-900 hover:bg-slate-850 text-white rounded text-xs font-bold border border-slate-800 transition flex items-center justify-center gap-2"
              >
                {loadingConnect ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Connect OneDrive"}
              </button>
            </div>
          </div>
        </div>

        {/* Center Column - Directories Configuration */}
        <div className="space-y-6 md:col-span-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Connected Accounts List */}
            <div className="p-5 bg-slate-950 border border-slate-900 rounded-xl shadow-md flex flex-col">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                <Cloud className="h-4 w-4 text-emerald-500" />
                3. Connected Integration Nodes
              </div>
              
              {loadingAccounts ? (
                <div className="flex justify-center py-10">
                  <Loader2 className="h-6 w-6 animate-spin text-slate-600" />
                </div>
              ) : accounts.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-600 font-semibold border border-dashed border-slate-900 rounded">
                  No active cloud accounts configured for this project.
                </div>
              ) : (
                <div className="space-y-2 overflow-y-auto max-h-60">
                  {accounts.map((acc) => (
                    <button
                      key={acc.id}
                      onClick={() => setActiveAccount(acc)}
                      className={`w-full text-left p-3 rounded border text-xs transition flex items-center justify-between ${
                        activeAccount?.id === acc.id
                          ? "bg-blue-950/40 text-blue-300 border-blue-900"
                          : "bg-slate-900/50 text-slate-400 border-slate-800 hover:bg-slate-900"
                      }`}
                    >
                      <div>
                        <div className="font-bold text-white capitalize">{acc.provider.replace("_", " ")}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">{acc.account_email}</div>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-600" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Folder Mapping Configuration */}
            {activeAccount && (
              <div className="p-5 bg-slate-950 border border-slate-900 rounded-xl shadow-md flex flex-col">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
                  <FolderOpen className="h-4 w-4 text-amber-500" />
                  4. Directory Target Sync Folder
                </div>
                
                {loadingFolders ? (
                  <div className="flex justify-center py-10">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-600" />
                  </div>
                ) : cloudFolders.length === 0 ? (
                  <div className="text-center py-10 text-xs text-slate-600 font-semibold">
                    No folders found in this cloud account.
                  </div>
                ) : (
                  <div className="space-y-4 flex-1 flex flex-col justify-between">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 mb-2">Select Cloud Folder</label>
                      <select
                        value={selectedFolderId}
                        onChange={(e) => setSelectedFolderId(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      >
                        {cloudFolders.map((f) => (
                          <option key={f.id} value={f.id}>
                            {f.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={handleConfigureSync}
                      className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-bold transition flex items-center justify-center gap-2 shadow"
                    >
                      <Play className="h-3.5 w-3.5" />
                      Bind & Start Incremental Sync
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sync History & Execution Logs Auditing */}
          {activeAccount && (
            <div className="p-5 bg-slate-950 border border-slate-900 rounded-xl shadow-md">
              <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <Clock className="h-4 w-4 text-blue-500 animate-pulse" />
                  Incremental Sync executions Jobs History
                </div>
                <button
                  onClick={loadSyncHistory}
                  disabled={loadingJobs}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-white transition font-bold"
                >
                  <RefreshCw className={`h-3 w-3 ${loadingJobs ? "animate-spin text-blue-500" : ""}`} />
                  Refresh Jobs
                </button>
              </div>

              {loadingJobs && syncJobs.length === 0 ? (
                <div className="flex justify-center py-10">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                </div>
              ) : syncJobs.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-600 font-semibold leading-relaxed">
                  No sync job records found. Start folders synchronization above to run incremental audits.
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto max-h-80">
                  {syncJobs.map((job) => (
                    <div
                      key={job.id}
                      className="p-3 bg-slate-900/40 border border-slate-900 rounded-lg flex items-center justify-between text-xs gap-4 font-mono"
                    >
                      <div className="flex items-center gap-3">
                        {job.status === "completed" ? (
                          <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0" />
                        ) : job.status === "running" ? (
                          <Loader2 className="h-5 w-5 text-blue-500 animate-spin flex-shrink-0" />
                        ) : (
                          <XCircle className="h-5 w-5 text-rose-500 flex-shrink-0" />
                        )}
                        <div>
                          <div className="font-bold text-slate-200">
                            Job ID: {job.id.substring(0, 8)}... (Added: {job.files_added} | Upd: {job.files_updated} | Del: {job.files_deleted})
                          </div>
                          <div className="text-[10px] text-slate-500 mt-1">
                            Started: {new Date(job.started_at).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      {job.error_message && (
                        <div className="text-[10px] text-rose-500 max-w-xs truncate" title={job.error_message}>
                          Error: {job.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
