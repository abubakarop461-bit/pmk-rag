"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { 
  Loader2, 
  ArrowLeft, 
  Upload, 
  History, 
  Trash2, 
  FileText,
  Calendar,
  X,
  User,
  Activity,
  Layers,
  Sparkles,
  CheckCircle2,
  XCircle
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

interface Revision {
  id: string;
  revision_number: string;
  file_size: number;
  mime_type: string;
  checksum: string;
  processing_status: string;
  error_message?: string | null;
  created_by?: string;
  created_at: string;
}

interface Document {
  id: string;
  document_name: string;
  document_type: string;
  created_at: string;
  latest_revision?: Revision;
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ProjectDetailsPage({ params }: PageProps) {
  const router = useRouter();
  const { user, session, loading: authLoading } = useAuth();
  
  // Resolve params Promise
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const [project, setProject] = useState<Project | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadType, setUploadType] = useState("contract");
  const [uploadRev, setUploadRev] = useState("A");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [aiType, setAiType] = useState<string | null>(null);
  const [aiConfidence, setAiConfidence] = useState<number | null>(null);
  const [showTypeSelector, setShowTypeSelector] = useState(false);

  // Version History Modal State
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loadingRevisions, setLoadingRevisions] = useState(false);

  const [devMode, setDevMode] = useState(false);
  const [justCompletedDoc, setJustCompletedDoc] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user || !projectId) return;

    let token = "demo_token";
    if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") {
      token = session?.access_token || "";
    }
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const sseUrl = `${backendUrl}/documents/project/${projectId}/events`;

    let active = true;
    let controller = new AbortController();

    async function connectSSE() {
      try {
        const response = await fetch(sseUrl, {
          headers: {
            "Authorization": `Bearer ${token}`
          },
          signal: controller.signal
        });

        if (!response.body) return;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (active) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const rawData = line.replace(/^data:\s*/, "").trim();
            if (!rawData) continue;

            try {
              const event = JSON.parse(rawData);
              if (event.event === "connected") {
                console.log("SSE connected successfully.");
                continue;
              }

              if (event.revision_id) {
                setDocuments((prevDocs) => {
                  let docName = "";
                  const updatedDocs = prevDocs.map((doc) => {
                    if (doc.latest_revision && doc.latest_revision.id === event.revision_id) {
                      docName = doc.document_name;
                      return {
                        ...doc,
                        latest_revision: {
                          ...doc.latest_revision,
                          processing_status: event.processing_status,
                          error_message: event.error_message,
                          processing_timings: event.processing_timings
                        }
                      };
                    }
                    return doc;
                  });

                  if ((event.processing_status === "ready" || event.processing_status === "completed") && docName) {
                    setJustCompletedDoc(docName);
                  }

                  return updatedDocs;
                });
              }
            } catch (err) {
              console.error("Failed to parse SSE document event payload", err);
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("SSE connection error, retrying in 5 seconds...", err);
          setTimeout(() => {
            if (active) connectSSE();
          }, 5000);
        }
      }
    }

    connectSSE();

    return () => {
      active = false;
      controller.abort();
    };
  }, [user, authLoading, projectId, session]);


  const renderStatusBadge = (status: string, errorMsg?: string | null) => {
    switch (status) {
      case "ready":
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-900/60">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            Ready to Chat
          </span>
        );
      case "failed":
        let tooltipText = "Processing failed.";
        if (errorMsg) {
          try {
            const parsedErr = JSON.parse(errorMsg);
            tooltipText = `Stage: ${parsedErr.failed_stage}\nException: ${parsedErr.exception}\nTime: ${parsedErr.timestamp}`;
          } catch {
            tooltipText = errorMsg;
          }
        }
        return (
          <span 
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-400 border border-rose-900/60 cursor-help"
            title={tooltipText}
          >
            <XCircle className="h-3.5 w-3.5 text-rose-400" />
            Failed
          </span>
        );
      case "pending":
      case "queued":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />
            Uploading...
          </span>
        );
      case "validating":
      case "parsing":
      case "ocr":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-950 text-blue-300 border border-blue-800 animate-pulse">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
            Reading document...
          </span>
        );
      case "metadata_extraction":
      case "chunking":
      case "embedding":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800 animate-pulse">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
            Understanding content...
          </span>
        );
      case "indexing":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-violet-950 text-violet-300 border border-violet-800 animate-pulse">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
            Preparing AI...
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {status}
          </span>
        );
    }
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch project details
      const projRes = await apiClient.get(`/api/projects/${projectId}`);
      setProject(projRes.data);

      // Fetch project documents
      const docsRes = await apiClient.get(`/api/documents/project/${projectId}`);
      setDocuments(docsRes.data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to load project details or documents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && projectId) {
      fetchData();
    }
  }, [user, projectId]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      alert("Please select a file to upload.");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("document_type", uploadType);
    formData.append("revision_number", uploadRev);
    if (aiType) {
      formData.append("ai_classified_type", aiType);
    }

    try {
      await apiClient.post(`/api/documents/project/${projectId}/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setShowUploadModal(false);
      setSelectedFile(null);
      setUploadRev("A");
      setAiType(null);
      setAiConfidence(null);
      setShowTypeSelector(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to upload document revision.");
    } finally {
      setUploading(false);
    }
  };

  const handleOpenHistory = async (doc: Document) => {
    setSelectedDoc(doc);
    setLoadingRevisions(true);
    try {
      const res = await apiClient.get(`/api/documents/${doc.id}/revisions`);
      setRevisions(res.data);
    } catch (err: any) {
      alert("Failed to load revision history.");
    } finally {
      setLoadingRevisions(false);
    }
  };

  const handleDeleteDoc = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete '${name}' and all its versions? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiClient.delete(`/api/documents/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete document.");
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 p-8 flex flex-col items-center gap-4">
        <div className="bg-rose-950/50 border border-rose-800 rounded-lg p-6 max-w-md text-center">
          <p className="text-rose-400 font-bold">Error Loading Page</p>
          <p className="text-slate-300 text-sm mt-2">{error || "Project metadata was not found."}</p>
          <Link href="/" className="mt-4 inline-flex items-center gap-2 text-blue-400 hover:underline text-sm font-semibold">
            <ArrowLeft className="h-4 w-4" /> Go back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const hasReadyDocument = documents.some(
    (doc) => doc.latest_revision?.processing_status === "ready" || doc.latest_revision?.processing_status === "completed"
  );

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Header bar */}
      <nav className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:text-blue-400 transition font-semibold text-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Projects
        </Link>
        <span className="text-sm text-slate-400 font-semibold">{project.name}</span>
      </nav>

      {/* Main layout grid */}
      <main className="max-w-6xl mx-auto px-6 py-10 grid gap-8 md:grid-cols-4">
        {/* Left Side: Metadata Card */}
        <div className="md:col-span-1 flex flex-col gap-6">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-6 shadow-lg">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Project Specification</h2>
            <h3 className="text-xl font-bold mt-2 text-white">{project.name}</h3>
            
            <div className="mt-4 flex flex-col gap-3 text-sm border-t border-slate-900 pt-4">
              <div>
                <span className="text-slate-500 block text-xs">Project ID</span>
                <span className="font-semibold">{project.project_number}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Client Owner</span>
                <span className="font-semibold">{project.client_name || "N/A"}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Creation Date</span>
                <span className="font-semibold text-xs flex items-center gap-1.5 mt-0.5">
                  <Calendar className="h-3.5 w-3.5 text-blue-500" />
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Workflow Status</span>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-900/50 text-blue-300 border border-blue-800 uppercase mt-1 inline-block">
                  {project.status}
                </span>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-6 shadow-lg text-slate-400 text-xs flex flex-col gap-2">
            <h4 className="font-bold text-white uppercase">AI Search Ready</h4>
            <p>Database schema fully tracks document changes and revisions. AI pipeline indexing starts in Phase 3.</p>
          </div>
        </div>

        {/* Right Side: Documents Grid */}
        <div className="md:col-span-3 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white">Engineering Documents</h2>
              <p className="text-sm text-slate-400 mt-1">Upload specs, drawings, or contract revisions.</p>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-400 cursor-pointer mr-2 select-none">
                <input
                  type="checkbox"
                  checked={devMode}
                  onChange={(e) => setDevMode(e.target.checked)}
                  className="rounded border-slate-800 bg-slate-950 text-blue-600 focus:ring-blue-500"
                />
                🔧 Developer Mode
              </label>
              {hasReadyDocument && (
                <Link
                  href={`/chat?project_id=${projectId}`}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-semibold transition text-sm shadow-lg shadow-emerald-950/20"
                >
                  <Sparkles className="h-4 w-4" />
                  Chat with Project
                </Link>
              )}
              <button
                onClick={() => setShowUploadModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-semibold transition text-sm"
              >
                <Upload className="h-4 w-4" />
                Upload Document
              </button>
            </div>
          </div>

          {justCompletedDoc && (
            <div className="bg-emerald-950/70 border border-emerald-500 rounded-lg p-4 flex items-center justify-between text-emerald-300 animate-pulse">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <span>✅ Your document '{justCompletedDoc}' is ready.</span>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  href={`/chat?project_id=${projectId}`}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded transition"
                >
                  Open Chat →
                </Link>
                <button
                  onClick={() => setJustCompletedDoc(null)}
                  className="text-emerald-500 hover:text-emerald-200 transition p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}


          {documents.length === 0 ? (
            <div className="border border-dashed border-slate-800 rounded-xl p-16 text-center flex flex-col items-center gap-4 bg-slate-950">
              <FileText className="h-12 w-12 text-slate-600" />
              <div>
                <h3 className="text-lg font-bold text-white">No documents uploaded</h3>
                <p className="text-slate-400 text-sm mt-1">Click upload to add specifications, contracts, or engineering drawings.</p>
              </div>
              <button
                onClick={() => setShowUploadModal(true)}
                className="mt-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded text-white font-semibold transition text-sm"
              >
                Upload File
              </button>
            </div>
          ) : (
            <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden shadow-lg">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 text-xs font-semibold uppercase">
                    <tr>
                      <th className="px-6 py-4">Filename</th>
                      <th className="px-6 py-4">Document Type</th>
                      <th className="px-6 py-4">Active Rev</th>
                      <th className="px-6 py-4">File Size</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-900/50 transition">
                        <td className="px-6 py-4 truncate max-w-xs">
                          <div className="font-semibold text-white">{doc.document_name}</div>
                          <div className="text-xs text-slate-500 mt-1">
                            Uploaded: {doc.latest_revision ? new Date(doc.latest_revision.created_at).toLocaleString() : "N/A"}
                          </div>
                          {devMode && doc.latest_revision?.processing_timings && (
                            <div className="text-[10px] text-slate-500 font-mono mt-2 bg-slate-900/60 p-2 rounded border border-slate-800/80 max-w-xs">
                              <div className="font-bold text-slate-400 mb-1">⏱️ Milestones:</div>
                              <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
                                <div>Upload: {doc.latest_revision.processing_timings.upload_ms ?? 0}ms</div>
                                <div>Validation: {doc.latest_revision.processing_timings.validation_ms ?? 0}ms</div>
                                <div>Parsing: {doc.latest_revision.processing_timings.parsing_ms ?? 0}ms</div>
                                <div>OCR: {doc.latest_revision.processing_timings.ocr_ms ?? 0}ms</div>
                                <div>Metadata: {doc.latest_revision.processing_timings.metadata_extraction_ms ?? 0}ms</div>
                                <div>Chunking: {doc.latest_revision.processing_timings.chunking_ms ?? 0}ms</div>
                                <div>Embedding: {doc.latest_revision.processing_timings.embedding_ms ?? 0}ms</div>
                                <div>Indexing: {doc.latest_revision.processing_timings.indexing_ms ?? 0}ms</div>
                                <div className="text-emerald-400 font-bold col-span-2 mt-0.5 pt-0.5 border-t border-slate-800">
                                  Total: {doc.latest_revision.processing_timings.total_ms ?? 0}ms
                                </div>
                              </div>
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 capitalize text-slate-300">
                          {doc.document_type}
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700">
                            Rev {doc.latest_revision?.revision_number || "N/A"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-400 text-xs">
                          {doc.latest_revision ? formatBytes(doc.latest_revision.file_size) : "N/A"}
                        </td>
                        <td className="px-6 py-4">
                          {renderStatusBadge(
                            doc.latest_revision?.processing_status || "pending",
                            doc.latest_revision?.error_message
                          )}
                        </td>
                        <td className="px-6 py-4 text-right flex items-center justify-end gap-3">
                          <button
                            onClick={() => handleOpenHistory(doc)}
                            className="flex items-center gap-1 text-xs text-slate-400 hover:text-blue-400 transition"
                            title="View Revision Chain"
                          >
                            <History className="h-4 w-4" />
                            History
                          </button>
                          <button
                            onClick={() => handleDeleteDoc(doc.id, doc.document_name)}
                            className="text-slate-600 hover:text-rose-500 transition"
                            title="Delete Document"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Upload File Dialog Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 max-w-md w-full shadow-2xl flex flex-col gap-6 relative">
            <button 
              onClick={() => setShowUploadModal(false)}
              className="absolute right-4 top-4 text-slate-500 hover:text-white transition"
            >
              <X className="h-5 w-5" />
            </button>
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Upload className="h-5 w-5 text-blue-500" />
                Upload New Document
              </h3>
              <p className="text-sm text-slate-400 mt-1">Files are saved locally. AI parsing occurs in downstream modules.</p>
            </div>

            <form onSubmit={handleUploadSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-sm font-semibold text-slate-300">Select Document File</label>
                <input
                  type="file"
                  required
                  onChange={async (e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      const fileObj = e.target.files[0];
                      setSelectedFile(fileObj);
                      
                      // Trigger AI Classification
                      setClassifying(true);
                      setAiType(null);
                      setAiConfidence(null);
                      setShowTypeSelector(false);
                      
                      const cData = new FormData();
                      cData.append("file", fileObj);
                      try {
                        const res = await apiClient.post("/api/documents/classify", cData, {
                          headers: { "Content-Type": "multipart/form-data" }
                        });
                        const detected = res.data.detected_document_type;
                        const conf = res.data.confidence_score;
                        
                        setAiType(detected);
                        setAiConfidence(conf);
                        setUploadType(detected);
                        
                        if (conf < 80) {
                          setShowTypeSelector(true);
                        } else {
                          setShowTypeSelector(false);
                        }
                      } catch (err) {
                        console.error("AI Document classification failed:", err);
                        setShowTypeSelector(true); // Fallback to manual selection on error
                      } finally {
                        setClassifying(false);
                      }
                    }
                  }}
                  className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-sm text-slate-400 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-300 file:hover:bg-slate-700 cursor-pointer"
                />
              </div>

              {classifying && (
                <div className="flex items-center gap-2 text-sm text-blue-400 py-1 px-3 bg-blue-950/40 border border-blue-900/50 rounded-lg animate-pulse">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>AI is classifying document...</span>
                </div>
              )}

              {selectedFile && !classifying && aiType && (
                <div className="flex flex-col gap-2">
                  {aiConfidence && aiConfidence >= 80 ? (
                    <div className="p-3 bg-emerald-950/40 border border-emerald-900/50 rounded-lg text-emerald-400 flex flex-col gap-1">
                      <div className="flex items-center justify-between text-sm font-semibold">
                        <span className="flex items-center gap-1">
                          <CheckCircle2 className="h-4 w-4" />
                          AI Classified: {aiType.replace('_', ' ')}
                        </span>
                        <span className="text-xs bg-emerald-900/60 px-1.5 py-0.5 rounded text-emerald-300">
                          {aiConfidence}% Match
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowTypeSelector(!showTypeSelector)}
                        className="text-xs text-left underline text-slate-400 hover:text-white transition mt-1 w-max"
                      >
                        {showTypeSelector ? "Hide Manual Override" : "Manual Override / Change Type"}
                      </button>
                    </div>
                  ) : (
                    <div className="p-3 bg-amber-950/40 border border-amber-900/50 rounded-lg text-amber-400 flex flex-col gap-1">
                      <div className="flex items-center justify-between text-sm font-semibold">
                        <span className="flex items-center gap-1">
                          <XCircle className="h-4 w-4" />
                          Low-Confidence detection: {aiType.replace('_', ' ')}
                        </span>
                        <span className="text-xs bg-amber-900/60 px-1.5 py-0.5 rounded text-amber-300">
                          {aiConfidence}% Match
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">Please confirm or change the document type classification below.</p>
                    </div>
                  )}
                </div>
              )}

              {(showTypeSelector || (aiConfidence && aiConfidence < 80) || (!selectedFile)) && (
                <div className="flex flex-col gap-1">
                  <label className="text-sm font-semibold text-slate-300">
                    {selectedFile ? "Confirm / Select Document Type" : "Document Type"}
                  </label>
                  <select
                    value={uploadType}
                    onChange={(e) => setUploadType(e.target.value)}
                    className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-blue-500 transition capitalize text-sm"
                  >
                    <option value="contract">contract</option>
                    <option value="specification">specification</option>
                    <option value="BOQ">BOQ</option>
                    <option value="RFI">RFI</option>
                    <option value="drawing">drawing</option>
                    <option value="technical_submittal">technical submittal</option>
                    <option value="method_statement">method statement</option>
                    <option value="NCR">NCR</option>
                    <option value="other">other</option>
                  </select>
                </div>
              )}

              <div className="flex flex-col gap-1">
                <label className="text-sm font-semibold text-slate-300">Revision Identifier</label>
                <input
                  type="text"
                  required
                  value={uploadRev}
                  onChange={(e) => setUploadRev(e.target.value)}
                  placeholder="e.g. A, B, C or 01"
                  className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-blue-500 transition text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={uploading || classifying || !selectedFile}
                className="w-full mt-2 py-2 rounded bg-blue-600 hover:bg-blue-500 transition text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
              >
                {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Index File Revision"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Version History Modal Dialog */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 max-w-2xl w-full shadow-2xl flex flex-col gap-6 relative">
            <button 
              onClick={() => setSelectedDoc(null)}
              className="absolute right-4 top-4 text-slate-500 hover:text-white transition"
            >
              <X className="h-5 w-5" />
            </button>
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Layers className="h-5 w-5 text-blue-500" />
                Revision History Chain
              </h3>
              <p className="text-sm text-slate-400 mt-1">
                Document: <b className="text-slate-200">{selectedDoc.document_name}</b>
              </p>
            </div>

            {loadingRevisions ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              </div>
            ) : (
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 text-xs uppercase font-semibold">
                    <tr>
                      <th className="px-6 py-3">Revision</th>
                      <th className="px-6 py-3">File Size</th>
                      <th className="px-6 py-3">Uploaded Date</th>
                      <th className="px-6 py-3">Uploader UUID</th>
                      <th className="px-6 py-3">SHA256 Checksum</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900 text-slate-300">
                    {revisions.map((rev) => (
                      <tr key={rev.id} className="hover:bg-slate-900/50 transition">
                        <td className="px-6 py-4 font-bold text-white">Rev {rev.revision_number}</td>
                        <td className="px-6 py-4 text-xs">{formatBytes(rev.file_size)}</td>
                        <td className="px-6 py-4 text-xs">
                          {new Date(rev.created_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-slate-500 truncate max-w-[100px]" title={rev.created_by}>
                          {rev.created_by || "system"}
                        </td>
                        <td className="px-6 py-4 text-xs font-mono text-slate-500 truncate max-w-[120px]" title={rev.checksum}>
                          {rev.checksum}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            <div className="flex justify-end pt-4 border-t border-slate-900">
              <button
                onClick={() => setSelectedDoc(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded font-semibold text-sm transition"
              >
                Close History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
