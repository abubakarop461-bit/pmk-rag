"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { 
  Search, 
  Filter, 
  Clock, 
  Layers, 
  Award, 
  ArrowLeft, 
  Compass, 
  ListFilter,
  CheckCircle,
  HelpCircle,
  FileSpreadsheet,
  FileText,
  Activity,
  Maximize2
} from "lucide-react";
import Link from "next/link";

interface Project {
  id: string;
  name: string;
  project_number: string;
}

interface ContextBlock {
  text: string;
  document_id: string;
  project_id: string;
  revision_id: string;
  filename: string;
  document_type: string;
  pages: number[];
  chunk_indexes: number[];
  vector_score: number;
  keyword_score: number;
  rerank_score: number;
  explain: string;
}

interface Citation {
  document_id: string;
  filename: string;
  pages: number[];
  document_type: string;
}

interface ContextPackage {
  context_blocks: ContextBlock[];
  confidence_summary: string;
  total_estimated_tokens: number;
  citations: Citation[];
}

interface Timings {
  preprocessing_ms: number;
  vector_search_ms: number;
  keyword_search_ms: number;
  rerank_ms: number;
  context_build_ms: number;
  total_ms: number;
}

interface SearchResponse {
  query: string;
  detected_intent: string;
  applied_filters: Record<string, any>;
  context_package: ContextPackage;
  timings: Timings;
}

export default function RetrievalTestingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Search parameters
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState("all");
  const [revision, setRevision] = useState("");
  const [enableHybrid, setEnableHybrid] = useState(true);
  const [alpha, setAlpha] = useState(0.5);

  // Search results
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    const fetchProjects = async () => {
      setLoadingProjects(true);
      try {
        const res = await apiClient.get("/projects");
        setProjects(res.data);
        if (res.data.length > 0) {
          setSelectedProject(res.data[0].id);
        }
      } catch (err) {
        console.error("Failed to load projects", err);
      } finally {
        setLoadingProjects(false);
      }
    };
    if (user) {
      fetchProjects();
    }
  }, [user]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) {
      alert("Please select a construction project to search within.");
      return;
    }
    if (!query.trim()) {
      alert("Please enter a search query.");
      return;
    }

    setSearching(true);
    setError(null);
    setResults(null);

    const payloadFilters: Record<string, any> = {};
    if (docType !== "all") {
      payloadFilters["document_type"] = docType;
    }
    if (revision.trim()) {
      payloadFilters["revision_number"] = revision.trim();
    }

    try {
      const res = await apiClient.post("/retrieval/search", {
        query: query,
        project_id: selectedProject,
        filters: Object.keys(payloadFilters).length > 0 ? payloadFilters : null,
        enable_hybrid: enableHybrid,
        alpha: alpha
      });
      setResults(res.data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || "Retrieval engine query failed.");
    } finally {
      setSearching(false);
    }
  };

  if (authLoading || loadingProjects) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <Activity className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Header bar */}
      <nav className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 hover:text-blue-400 transition font-semibold text-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Dashboard
        </Link>
        <span className="text-sm text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
          <Compass className="h-4 w-4 text-blue-500" />
          Retrieval Diagnostics Console
        </span>
      </nav>

      {/* Main split grid */}
      <main className="max-w-7xl mx-auto px-6 py-10 grid gap-8 lg:grid-cols-3">
        {/* Left Side: Search Controls */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-5">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Filter className="h-5 w-5 text-blue-500" />
                Query Filters
              </h2>
              <p className="text-xs text-slate-500 mt-1">Scope semantic query ranges across projects and document parameters.</p>
            </div>

            <form onSubmit={handleSearch} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase">Target Project</label>
                <select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-800 text-sm focus:outline-none focus:border-blue-500 transition text-slate-200"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} (#{p.project_number})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase">Query Expression</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="e.g. wet burlap concrete specs"
                    className="w-full pl-3 pr-10 py-2 rounded bg-slate-900 border border-slate-800 text-sm placeholder-slate-600 focus:outline-none focus:border-blue-500 transition text-white font-medium"
                  />
                  <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-blue-400 transition">
                    <Search className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="border-t border-slate-900 pt-4 flex flex-col gap-4">
                <h3 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-1.5">
                  <ListFilter className="h-3.5 w-3.5" />
                  Metadata Restrictions
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-slate-400">Doc Type</label>
                    <select
                      value={docType}
                      onChange={(e) => setDocType(e.target.value)}
                      className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs focus:outline-none focus:border-blue-500 transition capitalize"
                    >
                      <option value="all">Any Type</option>
                      <option value="contract">contract</option>
                      <option value="specification">specification</option>
                      <option value="BOQ">BOQ</option>
                      <option value="drawing">drawing</option>
                      <option value="technical_submittal">technical submittal</option>
                      <option value="method_statement">method statement</option>
                      <option value="NCR">NCR</option>
                      <option value="other">other</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-xs text-slate-400">Revision</label>
                    <input
                      type="text"
                      value={revision}
                      onChange={(e) => setRevision(e.target.value)}
                      placeholder="e.g. A, B"
                      className="px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs placeholder-slate-700 focus:outline-none focus:border-blue-500 transition"
                    />
                  </div>
                </div>
              </div>

              <div className="border-t border-slate-900 pt-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-400 uppercase flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableHybrid}
                      onChange={(e) => setEnableHybrid(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-800 text-blue-500 focus:ring-0 cursor-pointer h-4 w-4"
                    />
                    Enable BM25 Hybrid
                  </label>
                  <span className="text-[10px] text-blue-400 font-bold bg-blue-950 px-2 py-0.5 rounded border border-blue-900">
                    Qdrant Text Index
                  </span>
                </div>

                {enableHybrid && (
                  <div className="flex flex-col gap-1 mt-1">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Vector Weight (Alpha): {alpha}</span>
                      <span>BM25: {1 - alpha}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={alpha}
                      onChange={(e) => setAlpha(parseFloat(e.target.value))}
                      className="w-full accent-blue-500 cursor-pointer bg-slate-800 rounded-lg appearance-none h-1.5 mt-1"
                    />
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={searching}
                className="w-full mt-2 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-semibold transition text-sm flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {searching ? <Activity className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Run Retrieval Diagnostics
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Results & Timings */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {searching ? (
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-20 flex flex-col items-center justify-center gap-4 text-center">
              <Activity className="h-10 w-10 animate-spin text-blue-500" />
              <div>
                <h3 className="text-lg font-bold text-white">Running Hybrid Retrieval</h3>
                <p className="text-slate-500 text-xs mt-1">Generating query embeddings, scanning inverted index matches, and scoring cross-encoders...</p>
              </div>
            </div>
          ) : error ? (
            <div className="bg-rose-950/40 border border-rose-800 rounded-xl p-6 text-sm text-rose-300">
              <h3 className="font-bold">Retrieval Failure</h3>
              <p className="mt-1 text-xs text-rose-400">{error}</p>
            </div>
          ) : !results ? (
            <div className="border border-dashed border-slate-800 rounded-xl p-20 text-center flex flex-col items-center justify-center gap-4 bg-slate-950/30">
              <Compass className="h-12 w-12 text-slate-700" />
              <div>
                <h3 className="text-lg font-bold text-slate-400">Ready for diagnostics</h3>
                <p className="text-slate-500 text-xs mt-1">Enter a query expression on the left panel to test rank-merging metrics.</p>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {/* Timing metrics & intent dashboard */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 shadow-xl grid gap-6 md:grid-cols-3">
                <div className="md:col-span-1 flex flex-col justify-between border-b md:border-b-0 md:border-r border-slate-900 pb-4 md:pb-0 md:pr-6">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-500 uppercase">Predicted Intent</h4>
                    <div className="text-lg font-bold mt-1 text-white capitalize flex items-center gap-1.5">
                      <Award className="h-5 w-5 text-amber-500" />
                      {results.detected_intent.replace("_", " ")}
                    </div>
                  </div>
                  <div className="mt-4">
                    <h4 className="text-xs font-semibold text-slate-500 uppercase">Overall Confidence</h4>
                    <div className="text-lg font-bold mt-1 text-blue-400 flex items-center gap-1.5">
                      <CheckCircle className="h-5 w-5 text-blue-500" />
                      {results.context_package.confidence_summary}
                    </div>
                  </div>
                  <div className="mt-4">
                    <h5 className="text-[10px] text-slate-500 font-bold uppercase">Applied Filters</h5>
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {Object.entries(results.applied_filters).map(([k, v]) => (
                        <span key={k} className="text-[10px] bg-slate-900 text-slate-300 border border-slate-800 px-2 py-0.5 rounded font-mono">
                          {k}={v}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="md:col-span-2 flex flex-col gap-4">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase flex items-center gap-1">
                    <Clock className="h-4 w-4 text-blue-500" />
                    Latency Milestones
                  </h4>
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-900">
                      <span className="text-[10px] text-slate-500 block">Preprocess</span>
                      <span className="text-sm font-bold text-slate-200 mt-1 block">{results.timings.preprocessing_ms} ms</span>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-900">
                      <span className="text-[10px] text-slate-500 block">Vector Match</span>
                      <span className="text-sm font-bold text-slate-200 mt-1 block">{results.timings.vector_search_ms} ms</span>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-900">
                      <span className="text-[10px] text-slate-500 block">Keyword scroll</span>
                      <span className="text-sm font-bold text-slate-200 mt-1 block">{results.timings.keyword_search_ms} ms</span>
                    </div>
                    <div className="bg-slate-900/60 p-2.5 rounded border border-slate-900">
                      <span className="text-[10px] text-slate-500 block">Re-ranker</span>
                      <span className="text-sm font-bold text-slate-200 mt-1 block">{results.timings.rerank_ms} ms</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400 mt-1 bg-slate-900 px-3 py-1.5 rounded border border-slate-800">
                    <span>Total Roundtrip Processing Duration:</span>
                    <span className="font-extrabold text-blue-400 text-sm">{results.timings.total_ms} ms</span>
                  </div>
                </div>
              </div>

              {/* Chunks results list */}
              <div className="flex flex-col gap-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="h-5 w-5 text-blue-500" />
                  Top Merged Context Blocks ({results.context_package.context_blocks.length})
                </h3>

                {results.context_package.context_blocks.length === 0 ? (
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-10 text-center text-slate-500 text-sm">
                    Zero document chunks matched this filter query. Try relaxation parameter modifications.
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {results.context_package.context_blocks.map((block, idx) => (
                      <div 
                        key={idx} 
                        className="bg-slate-950 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition flex flex-col gap-4 shadow-lg group relative"
                      >
                        {/* Chunk header details */}
                        <div className="flex items-center justify-between border-b border-slate-900 pb-3 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-950 text-blue-300 border border-blue-900 capitalize">
                              {block.document_type}
                            </span>
                            <span className="font-semibold text-slate-200 truncate max-w-[180px]" title={block.filename}>
                              {block.filename}
                            </span>
                            <span className="text-slate-600">•</span>
                            <span className="text-slate-400">Pages {block.pages.join(", ")} (Chunks {block.chunk_indexes.join(", ")})</span>
                          </div>
                          
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1" title="Cosine Vector similarity score">
                              <span className="text-[10px] text-slate-500">Vector:</span>
                              <span className="font-bold text-slate-300">{block.vector_score.toFixed(3)}</span>
                            </div>
                            <div className="flex items-center gap-1" title="Inverted scroll index keyword match check">
                              <span className="text-[10px] text-slate-500">Keyword:</span>
                              <span className="font-bold text-slate-300">{block.keyword_score.toFixed(1)}</span>
                            </div>
                            <div className="flex items-center gap-1 bg-blue-950/80 px-2 py-0.5 rounded border border-blue-900 text-blue-300 font-bold" title="Cross-Encoder BAAI rerank score">
                              <span>Rerank Score:</span>
                              <span>{block.rerank_score.toFixed(3)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Chunk body text */}
                        <p className="text-sm text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
                          {block.text}
                        </p>

                        {/* Explainability footnote */}
                        <div className="text-[10px] text-slate-500 bg-slate-900/30 border border-slate-900/60 p-2.5 rounded font-mono mt-1">
                          <span className="font-bold text-slate-400">Explain:</span> {block.explain}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
