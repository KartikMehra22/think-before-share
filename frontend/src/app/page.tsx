"use client";

import React, { useState, useEffect } from "react";
import { 
  Youtube, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  HelpCircle, 
  ArrowRight, 
  ShieldCheck, 
  Search, 
  AlertCircle,
  ExternalLink,
  Share2,
  RefreshCw
} from "lucide-react";

interface Claim {
  id: string;
  claim: string;
  speaker?: string;
  timestamp?: string;
  status: "Supported" | "Needs Context" | "Contradicted" | "Insufficient Evidence";
  evidence: string;
  sourceUrl: string;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [apiStatus, setApiStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [backendMessage, setBackendMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showDemo, setShowDemo] = useState(true);

  // Simulated Claims for visual excellence (Hackathon Demo state)
  const demoClaims: Claim[] = [
    {
      id: "claim-1",
      claim: "NASA has confirmed a planet-killing asteroid will impact Earth in October 2026.",
      speaker: "Narrator",
      timestamp: "02:15",
      status: "Contradicted",
      evidence: "NASA's Planetary Defense Coordination Office has confirmed that there are no known asteroid threats with a significant impact probability for the next 100 years. The asteroid mentioned (2026 RF) will pass at a safe distance of 4.2 million miles.",
      sourceUrl: "https://www.nasa.gov/planetarydefense"
    },
    {
      id: "claim-2",
      claim: "Electric vehicles produce more lifetime carbon emissions than gas cars when manufacturing is included.",
      speaker: "Guest Expert",
      timestamp: "05:40",
      status: "Needs Context",
      evidence: "While EV manufacturing is carbon-intensive due to battery production, studies from Argonne National Laboratory and the EPA show that EVs recover this deficit within 1 to 2 years of operation and have significantly lower lifetime emissions than internal combustion engine vehicles.",
      sourceUrl: "https://www.epa.gov/greenvehicles/electric-vehicle-myths"
    },
    {
      id: "claim-3",
      claim: "Deepfakes are now highly prevalent in political campaigns, with over 100 detected cases in recent local elections.",
      speaker: "Narrator",
      timestamp: "12:10",
      status: "Supported",
      evidence: "Multiple reports from independent security watchdogs and election integrity groups confirm a sharp rise in artificial intelligence-generated media targeting local candidates, matching the figures cited.",
      sourceUrl: "https://www.reuters.com/fact-check"
    }
  ];

  // Check backend health on load
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch("http://localhost:8000/");
        if (response.ok) {
          const data = await response.json();
          setApiStatus("connected");
          setBackendMessage(data.message || "Healthy");
        } else {
          setApiStatus("disconnected");
        }
      } catch (error) {
        console.error("Backend connection failed:", error);
        setApiStatus("disconnected");
      }
    };
    checkBackend();
  }, []);

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setIsAnalyzing(true);
    // Simulate API call delay for visual polish
    setTimeout(() => {
      setIsAnalyzing(false);
      setShowDemo(true);
    }, 1500);
  };

  const getStatusBadge = (status: Claim["status"]) => {
    switch (status) {
      case "Supported":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Supported
          </span>
        );
      case "Needs Context":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" /> Needs Context
          </span>
        );
      case "Contradicted":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" /> Contradicted
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
            <HelpCircle className="w-3.5 h-3.5" /> Insufficient Evidence
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-purple-500/30 font-sans relative overflow-hidden flex flex-col justify-between">
      
      {/* Background Decorative Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-900/15 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-900/15 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="border-b border-slate-900 backdrop-blur-md bg-slate-950/60 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-purple-600/20 p-2 rounded-xl border border-purple-500/30">
              <ShieldCheck className="w-6 h-6 text-purple-400" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
              ThinkBeforeShare
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* API Status Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
              <span className={`w-2 h-2 rounded-full ${
                apiStatus === "connected" ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : 
                apiStatus === "disconnected" ? "bg-rose-500 shadow-[0_0_8px_#f43f5e]" : 
                "bg-amber-500 animate-pulse"
              }`} />
              <span className="text-xs text-slate-400 font-medium">
                {apiStatus === "connected" ? "API Online" : 
                 apiStatus === "disconnected" ? "API Offline" : "Connecting Backend..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow max-w-4xl mx-auto px-4 py-12 w-full">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 mb-4 text-xs font-semibold">
            <span>✨ Hackathon Prototype Scaffold</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4 bg-gradient-to-b from-white to-slate-400 bg-clip-text text-transparent">
            Verify Before You Share.
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Paste a YouTube URL to automatically transcribe, extract factual claims, and verify them against web sources using AI.
          </p>
        </div>

        {/* Search URL Form */}
        <div className="bg-slate-900/40 border border-slate-800 backdrop-blur-md rounded-2xl p-6 mb-12 shadow-2xl relative">
          <form onSubmit={handleAnalyze} className="flex flex-col md:flex-row gap-3">
            <div className="relative flex-grow">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Youtube className="w-5 h-5" />
              </div>
              <input
                id="youtube-url-input"
                type="url"
                required
                placeholder="Paste YouTube Video URL (e.g., https://www.youtube.com/watch?v=...)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-11 pr-4 py-3.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
              />
            </div>
            <button
              id="analyze-btn"
              type="submit"
              disabled={isAnalyzing}
              className="bg-purple-600 hover:bg-purple-500 text-white font-semibold px-6 py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-purple-900/30 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" /> Analyze Video
                </>
              )}
            </button>
          </form>

          {/* Backend Response Alert */}
          {apiStatus === "connected" && backendMessage && (
            <div className="mt-4 flex items-start gap-2 px-3.5 py-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/10 text-emerald-400 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Connected successfully to Python API!</strong> Response: "{backendMessage}"
              </span>
            </div>
          )}
        </div>

        {/* Claims Dashboard Display */}
        {showDemo && (
          <div className="space-y-8">
            <div className="flex items-center justify-between border-b border-slate-900 pb-3">
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <span>Claims Assessment Report</span>
                <span className="text-xs bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-normal">
                  3 Claims Extracted
                </span>
              </h2>
              <span className="text-xs text-slate-500">Video ID: Demo_Simulation</span>
            </div>

            {/* Claims Cards */}
            <div className="space-y-4">
              {demoClaims.map((claim) => (
                <div 
                  key={claim.id} 
                  className="bg-slate-900/30 border border-slate-900/60 rounded-xl p-5 hover:border-slate-800/80 transition-all"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="bg-slate-800/80 px-2 py-0.5 rounded font-mono">
                        TS {claim.timestamp}
                      </span>
                      {claim.speaker && (
                        <span>• Speaker: {claim.speaker}</span>
                      )}
                    </div>
                    {getStatusBadge(claim.status)}
                  </div>
                  
                  <blockquote className="text-base text-slate-200 font-medium mb-3 border-l-2 border-purple-500/30 pl-3">
                    "{claim.claim}"
                  </blockquote>
                  
                  <div className="bg-slate-950/60 rounded-lg p-3.5 border border-slate-900 text-sm text-slate-400">
                    <div className="text-xs text-slate-500 font-bold mb-1 tracking-wide uppercase">
                      Evidence Retrieval Summary
                    </div>
                    {claim.evidence}
                    {claim.sourceUrl && (
                      <div className="mt-3">
                        <a 
                          href={claim.sourceUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-purple-400 hover:text-purple-300 text-xs font-semibold"
                        >
                          View verified source <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* SIFT/Media Literacy Intervention Card */}
            <div className="bg-gradient-to-r from-purple-950/20 via-indigo-950/20 to-slate-900/20 border border-purple-900/30 rounded-2xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-3 bg-purple-500/10 border-b border-l border-purple-500/20 rounded-bl-xl text-purple-400 text-xs font-bold uppercase tracking-widest">
                Literacy Check
              </div>
              <h3 className="text-lg font-bold text-purple-300 mb-2 flex items-center gap-2">
                💡 Media Literacy Insights: The SIFT Method
              </h3>
              <p className="text-sm text-slate-400 mb-4 leading-relaxed">
                Before hitting share, remember to <strong>S</strong>top, <strong>I</strong>nvestigate the source, <strong>F</strong>ind better coverage, and <strong>T</strong>race the claim back to its original context.
              </p>
              
              {/* Verify before sharing screen */}
              <div className="border-t border-slate-900 pt-5 mt-5">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div>
                    <h4 className="text-sm font-bold text-slate-200">Verify Before You Share</h4>
                    <p className="text-xs text-slate-500">Pause sharing if claims are contradicted or need critical context.</p>
                  </div>
                  <div className="flex gap-2.5 w-full sm:w-auto">
                    <button
                      id="share-anyway-btn"
                      onClick={() => alert("Remember: sharing unverified claims feeds misinformation loops!")}
                      className="flex-1 sm:flex-initial px-4 py-2.5 rounded-lg border border-slate-800 text-xs font-semibold text-slate-400 hover:bg-slate-900/80 transition-all"
                    >
                      Share Anyway
                    </button>
                    <button
                      id="verify-share-btn"
                      onClick={() => alert("Thank you for practicing media literacy! Your verified share links are ready.")}
                      className="flex-1 sm:flex-initial bg-purple-600 hover:bg-purple-500 px-4 py-2.5 rounded-lg text-xs font-semibold text-white transition-all flex items-center justify-center gap-1.5"
                    >
                      <Share2 className="w-3.5 h-3.5" /> Share Verified Insights
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-8 bg-slate-950">
        <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500">
            &copy; {new Date().getFullYear()} ThinkBeforeShare. Hackathon Project. Powered by Gemini API & Tavily Search.
          </p>
          <div className="flex gap-4 text-xs text-slate-500">
            <a href="https://aistudio.google.com/" className="hover:text-slate-400">Gemini</a>
            <a href="https://tavily.com/" className="hover:text-slate-400">Tavily</a>
            <a href="https://github.com" className="hover:text-slate-400">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
