"use client";

import React, { useState } from "react";
import {
  Youtube,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Search,
  AlertCircle,
  ExternalLink,
  Share2,
  RefreshCw,
  Loader2,
  Info,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

interface EvidencedClaim {
  claim: string;
  search_query?: string | null;
  speaker: string | null;
  timestamp_hint: string | null;
  status: "Supported" | "Needs Context" | "Contradicted" | "Insufficient Evidence";
  confidence_score?: number;
  evidence_summary: string;
  sources: string[];
}

interface MediaSignal {
  signal_key: string;
  label: string;
  quote_snippet?: string | null;
  explanation?: string | null;
}

interface AnalysisResult {
  video_id: string;
  video_url: string;
  claims: EvidencedClaim[];
  trust_score?: number;
  credibility_tier?: string;
  overall_verdict: "Mostly Accurate" | "Mixed" | "Mostly Misleading" | "Unverifiable";
  literacy_tip: string;
  shareability_recommendation?: string;
  signals?: string[];
  detailed_signals?: MediaSignal[];
}

type AppState = "idle" | "loading" | "result" | "error";

const BACKEND_URL = "http://127.0.0.1:8000";

export default function Home() {
  const [url, setUrl] = useState("");
  const [appState, setAppState] = useState<AppState>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [loadingStep, setLoadingStep] = useState(0);

  const LOADING_STEPS = [
    "Extracting transcript…",
    "Identifying factual claims…",
    "Searching for evidence…",
    "Rating each claim…",
    "Generating literacy insights…",
  ];

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setAppState("loading");
    setErrorMsg("");
    setResult(null);
    setLoadingStep(0);

    try {
      const response = await fetch(`${BACKEND_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Analysis failed. Please try again.");
      }

      const { job_id } = await response.json();

      const poll = async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/analyze/${job_id}`);
          if (!res.ok) throw new Error("Failed to fetch job status");
          const job = await res.json();
          
          if (job.stage === "done") {
            setResult(job.result);
            setAppState("result");
          } else if (job.stage === "error") {
            throw new Error(job.error || "Analysis failed");
          } else {
            const completed = job.stages_complete?.length || 0;
            setLoadingStep(Math.min(completed, LOADING_STEPS.length - 1));
            setTimeout(poll, 1000);
          }
        } catch (err) {
          setErrorMsg(err instanceof Error ? err.message : "An unexpected error occurred.");
          setAppState("error");
        }
      };

      poll();

    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "An unexpected error occurred.");
      setAppState("error");
    }
  };

  const handleReset = () => {
    setAppState("idle");
    setResult(null);
    setErrorMsg("");
    setUrl("");
  };

  const getStatusConfig = (status: EvidencedClaim["status"]) => {
    switch (status) {
      case "Supported":
        return {
          badge: (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" /> Supported
            </span>
          ),
          bar: "bg-emerald-500",
        };
      case "Needs Context":
        return {
          badge: (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="w-3.5 h-3.5" /> Needs Context
            </span>
          ),
          bar: "bg-amber-500",
        };
      case "Contradicted":
        return {
          badge: (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <XCircle className="w-3.5 h-3.5" /> Contradicted
            </span>
          ),
          bar: "bg-rose-500",
        };
      default:
        return {
          badge: (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
              <HelpCircle className="w-3.5 h-3.5" /> Insufficient Evidence
            </span>
          ),
          bar: "bg-zinc-500",
        };
    }
  };

  const getVerdictConfig = (verdict: AnalysisResult["overall_verdict"], score: number = 50) => {
    if (score >= 80) {
      return { icon: <TrendingUp className="w-5 h-5 text-emerald-400" />, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" };
    } else if (score >= 50) {
      return { icon: <Minus className="w-5 h-5 text-amber-400" />, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" };
    } else {
      return { icon: <TrendingDown className="w-5 h-5 text-rose-400" />, color: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/20" };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-purple-500/30 font-sans flex flex-col relative overflow-hidden">
      {/* Decorative Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-900/15 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/15 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="border-b border-slate-900 backdrop-blur-md bg-slate-950/60 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <button onClick={handleReset} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <div className="bg-purple-600/20 p-2 rounded-xl border border-purple-500/30">
              <ShieldCheck className="w-6 h-6 text-purple-400" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
              ThinkBeforeShare
            </span>
          </button>
          {result && (
            <button
              onClick={handleReset}
              className="text-xs text-slate-400 hover:text-slate-200 transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 hover:border-slate-700"
            >
              <RefreshCw className="w-3.5 h-3.5" /> New Analysis
            </button>
          )}
        </div>
      </header>

      <main className="flex-grow max-w-5xl mx-auto px-4 py-12 w-full">
        {/* === IDLE / ERROR STATE — URL INPUT === */}
        {(appState === "idle" || appState === "error") && (
          <div className="flex flex-col items-center text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 mb-5 text-xs font-semibold">
              ✨ AI-Powered Media Literacy & Claim Verification
            </div>
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4 bg-gradient-to-b from-white to-slate-400 bg-clip-text text-transparent max-w-2xl">
              Verify Before You Share.
            </h1>
            <p className="text-slate-400 text-lg max-w-xl mb-10">
              Paste a YouTube URL. We'll extract claims, verify them against live web evidence, and score overall content credibility.
            </p>

            <div className="w-full max-w-2xl bg-slate-900/40 border border-slate-800 backdrop-blur-md rounded-2xl p-6 shadow-2xl">
              <form onSubmit={handleAnalyze} className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-grow">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Youtube className="w-5 h-5" />
                  </div>
                  <input
                    id="youtube-url-input"
                    type="url"
                    required
                    placeholder="https://www.youtube.com/watch?v=..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-3.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
                  />
                </div>
                <button
                  id="analyze-btn"
                  type="submit"
                  className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-6 py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-900/30 whitespace-nowrap"
                >
                  <Search className="w-4 h-4" /> Analyze Video
                </button>
              </form>

              {appState === "error" && (
                <div className="mt-4 flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-rose-500/5 border border-rose-500/20 text-rose-400 text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}
            </div>

            {/* How it works */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-12 w-full max-w-3xl text-left">
              {[
                { step: "1", label: "Paste URL", desc: "Any public YouTube video with captions" },
                { step: "2", label: "Extract Claims", desc: "Gemini AI extracts atomic factual claims" },
                { step: "3", label: "Search Evidence", desc: "Tavily queries live web fact-checks" },
                { step: "4", label: "Trust Score", desc: "Get credibility score & literacy tips" },
              ].map((item) => (
                <div key={item.step} className="bg-slate-900/30 border border-slate-900 rounded-xl p-4">
                  <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 text-xs font-bold flex items-center justify-center mb-2">
                    {item.step}
                  </div>
                  <div className="text-sm font-semibold text-slate-200 mb-1">{item.label}</div>
                  <div className="text-xs text-slate-500">{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* === LOADING STATE === */}
        {appState === "loading" && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-8">
            <div className="relative">
              <div className="w-20 h-20 rounded-full border-2 border-slate-800 flex items-center justify-center">
                <Loader2 className="w-10 h-10 text-purple-400 animate-spin" />
              </div>
              <div className="absolute inset-0 w-20 h-20 rounded-full border-t-2 border-purple-500 animate-spin" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-200 mb-2">Analyzing Video…</h2>
              <p className="text-purple-400 text-sm font-medium animate-pulse">
                {LOADING_STEPS[loadingStep]}
              </p>
              <p className="text-slate-500 text-xs mt-2">Checking transcript claims & live web evidence</p>
            </div>
            <div className="flex gap-2">
              {LOADING_STEPS.map((_, i) => (
                <div
                  key={i}
                  className={`h-1 rounded-full transition-all duration-500 ${
                    i <= loadingStep ? "w-8 bg-purple-500" : "w-2 bg-slate-800"
                  }`}
                />
              ))}
            </div>
          </div>
        )}

        {/* === RESULT STATE === */}
        {appState === "result" && result && (
          <div className="space-y-8">
            {/* Overall Verdict Header with Trust Score */}
            {(() => {
              const score = result.trust_score ?? 50;
              const vc = getVerdictConfig(result.overall_verdict, score);
              return (
                <div className={`rounded-2xl border p-6 ${vc.bg}`}>
                  <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Content Credibility</span>
                        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-900/80 text-slate-300 border border-slate-800">
                          {result.credibility_tier || "Caution / Mixed"}
                        </span>
                      </div>
                      <div className={`text-3xl font-extrabold flex items-center gap-2.5 ${vc.color}`}>
                        {vc.icon} {result.overall_verdict}
                      </div>
                      <p className="text-sm text-slate-300 mt-2.5 leading-relaxed max-w-2xl">{result.literacy_tip}</p>
                    </div>

                    {/* Trust Score Gauge */}
                    <div className="flex items-center gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-900 shrink-0">
                      <div className="text-center">
                        <div className="text-3xl font-black text-white font-mono">{score}%</div>
                        <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Trust Score</div>
                      </div>
                      <div className="w-12 h-12 rounded-full border-4 border-slate-800 flex items-center justify-center relative">
                        <div
                          className={`absolute inset-0 rounded-full border-4 ${
                            score >= 80 ? "border-emerald-500" : score >= 50 ? "border-amber-500" : "border-rose-500"
                          }`}
                          style={{ clipPath: `polygon(0 0, 100% 0, 100% ${score}%, 0 ${score}%)` }}
                        />
                        <ShieldCheck className="w-5 h-5 text-slate-400" />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Detailed Media Literacy Signals (Red Flags) */}
            {result.detailed_signals && result.detailed_signals.length > 0 && (
              <div className="bg-slate-900/40 border border-amber-500/20 rounded-2xl p-5">
                <h3 className="text-sm font-bold text-amber-400 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" /> Detected Media Literacy Red Flags
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.detailed_signals.map((sig, idx) => (
                    <div key={idx} className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 text-xs">
                      <div className="font-semibold text-slate-200 mb-1 text-sm">{sig.label}</div>
                      {sig.quote_snippet && (
                        <div className="italic text-amber-300/90 mb-1.5 border-l border-amber-500/40 pl-2">
                          "{sig.quote_snippet}"
                        </div>
                      )}
                      {sig.explanation && <div className="text-slate-400">{sig.explanation}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Claims */}
            <div>
              <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  Claim-by-Claim Verification
                  <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-normal">
                    {result.claims.length} claims
                  </span>
                </span>
              </h2>
              <div className="space-y-4">
                {result.claims.map((claim, idx) => {
                  const cfg = getStatusConfig(claim.status);
                  return (
                    <div
                      key={idx}
                      className="bg-slate-900/30 border border-slate-900/60 rounded-xl p-5 hover:border-slate-800 transition-all"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span className="bg-slate-800 px-2 py-0.5 rounded font-mono">#{idx + 1}</span>
                          {claim.speaker && <span>• {claim.speaker}</span>}
                          {claim.timestamp_hint && <span>• {claim.timestamp_hint}</span>}
                          {claim.confidence_score && (
                            <span className="bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded text-[11px] font-mono">
                              {Math.round(claim.confidence_score * 100)}% Confidence
                            </span>
                          )}
                        </div>
                        {cfg.badge}
                      </div>

                      <blockquote className="text-sm md:text-base text-slate-200 font-medium mb-3 border-l-2 border-purple-500/30 pl-3 leading-relaxed">
                        "{claim.claim}"
                      </blockquote>

                      <div className="bg-slate-950/60 rounded-lg p-3.5 border border-slate-900">
                        <div className="text-xs text-slate-500 font-bold mb-1.5 tracking-wide uppercase flex items-center gap-1">
                          <Info className="w-3 h-3" /> Fact-Check & Evidence
                        </div>
                        <p className="text-sm text-slate-300 leading-relaxed">{claim.evidence_summary}</p>
                        {claim.sources.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {claim.sources.slice(0, 4).map((src, i) => (
                              <a
                                key={i}
                                href={src}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-purple-400 hover:text-purple-300 text-xs font-medium bg-purple-500/5 border border-purple-500/10 px-2 py-1 rounded-lg"
                              >
                                Source {i + 1} <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Actionable Before You Share Guidance */}
            <div className="bg-gradient-to-r from-purple-950/20 via-indigo-950/20 to-slate-900/20 border border-purple-900/30 rounded-2xl p-6">
              <h3 className="text-base font-bold text-purple-300 mb-1 flex items-center gap-2">
                💡 Before You Share Recommendation
              </h3>
              <p className="text-sm text-slate-300 mb-5 leading-relaxed">
                {result.shareability_recommendation || "Remember to double check claims from primary news sources before forwarding."}
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  id="share-anyway-btn"
                  onClick={() => alert("⚠️ Sharing unverified claims fuels misinformation. Please double-check key facts first.")}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-800 text-sm font-semibold text-slate-400 hover:bg-slate-900/80 transition-all"
                >
                  Share Anyway
                </button>
                <button
                  id="verify-share-btn"
                  onClick={() => {
                    const score = result.trust_score ?? 50;
                    const text = `I fact-checked this video using ThinkBeforeShare!\nTrust Score: ${score}%\nVerdict: ${result.overall_verdict}\nVideo URL: ${result.video_url}`;
                    navigator.clipboard.writeText(text).then(() => alert("✅ Verified summary copied to clipboard!"));
                  }}
                  className="flex-1 bg-purple-600 hover:bg-purple-500 px-4 py-3 rounded-xl text-sm font-semibold text-white transition-all flex items-center justify-center gap-2"
                >
                  <Share2 className="w-4 h-4" /> Copy Fact-Checked Summary
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 bg-slate-950 mt-auto">
        <div className="max-w-5xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <p>&copy; {new Date().getFullYear()} ThinkBeforeShare — AI Claim Verification & Media Literacy.</p>
          <div className="flex gap-4">
            <a href="https://aistudio.google.com/" className="hover:text-slate-400">Gemini</a>
            <a href="https://tavily.com/" className="hover:text-slate-400">Tavily</a>
            <a href="https://github.com/KartikMehra22/think-before-share" className="hover:text-slate-400">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
