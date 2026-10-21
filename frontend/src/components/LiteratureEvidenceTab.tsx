import React from 'react';
import { UploadCloud, FileText, CheckCircle2, MessageSquare, Send, Bot, User, ArrowRight } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-transparent text-slate-900 font-sans p-0 flex justify-center">
      <div className="w-full max-w-5xl space-y-6">
        
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-sky-100 p-2 rounded-lg text-sky-600">
              <Bot className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
              ARIA - Evidence Bridge
            </h1>
          </div>
          <p className="text-slate-500 font-medium ml-11">
            Dynamic PDF Ingestion & Retrieval-Augmented Decision Support
          </p>
        </header>

        {/* Top Section: PDF Ingestion */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">
            Knowledge Base Ingestion
          </h2>
          <div className="border-2 border-dashed border-slate-300 rounded-xl bg-slate-50/50 hover:bg-sky-50/50 transition-colors cursor-pointer group p-10 flex flex-col items-center justify-center text-center">
            <div className="bg-white p-4 rounded-full shadow-sm mb-4 group-hover:scale-105 transition-transform">
              <UploadCloud className="w-8 h-8 text-sky-500" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">
              Upload Recent Clinical Studies & Whitepapers
            </h3>
            <p className="text-slate-500 mb-6 max-w-md">
              Drag and drop PDFs to add them to the evidence engine for instant cross-referencing against standard guidelines.
            </p>
            <button className="bg-sky-600 hover:bg-sky-700 text-white font-medium py-2.5 px-6 rounded-lg transition-colors flex items-center gap-2">
              <UploadCloud className="w-4 h-4" />
              Drop PDF or Browse Files
            </button>
          </div>
        </section>

        {/* Middle Section: Active Knowledge Base */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">
            Active Knowledge Base
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="flex items-start gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-900 leading-tight">AHA/ASA Stroke Guidelines</p>
                <p className="text-xs text-slate-500 mt-1">Fixed CPG</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-900 leading-tight">APTA Physical Therapy Guidelines</p>
                <p className="text-xs text-slate-500 mt-1">Fixed CPG</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3 p-4 rounded-xl border border-slate-100 bg-slate-50">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-900 leading-tight">ASHA / ROMA Guidelines</p>
                <p className="text-xs text-slate-500 mt-1">Fixed CPG</p>
              </div>
            </div>
            
            <div className="flex items-start gap-3 p-4 rounded-xl border border-sky-200 bg-sky-50 shadow-sm shadow-sky-100">
              <FileText className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-sky-950 leading-tight">High-Intensity Gait Training 2026.pdf</p>
                <p className="text-xs text-sky-700 mt-1 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-sky-500 inline-block"></span>
                  Active (User Uploaded)
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Bottom Section: Evidence Query Chat */}
        <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm flex flex-col h-[400px]">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-slate-500" />
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
              Evidence Query
            </h2>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
            
            {/* User Message */}
            <div className="flex gap-4 max-w-3xl">
              <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-slate-600" />
              </div>
              <div className="pt-1.5">
                <p className="text-slate-800 text-sm md:text-base leading-relaxed">
                  Does the uploaded gait study support 5x/week PT for a patient with BBS score of 38?
                </p>
              </div>
            </div>

            {/* AI Response */}
            <div className="flex gap-4 max-w-3xl">
              <div className="w-8 h-8 rounded-full bg-sky-600 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="pt-1 bg-sky-50 rounded-2xl rounded-tl-none p-5 text-sm md:text-base text-slate-800 leading-relaxed border border-sky-100">
                <p className="mb-3">
                  Yes, the uploaded study strongly supports this frequency.
                </p>
                <p className="mb-4">
                  According to the <span className="font-semibold text-sky-900">High-Intensity Gait Training 2026</span> guidelines (Page 12, Section 3.1), high-intensity stepping practice at 5 sessions per week is recommended to maximize neuroplasticity for patients with a Berg Balance Scale (BBS) score between 35-45, provided they can tolerate the cardiovascular demand.
                </p>
                <div className="bg-white p-3 rounded-lg border border-sky-200 text-xs text-slate-600 font-mono shadow-sm">
                  Citation: "Patients exhibiting a BBS score of &gt;35 demonstrate significant functional gains when engaged in 5x/week high-intensity gait protocols." (Pg. 12)
                </div>
              </div>
            </div>
            
          </div>

          <div className="p-4 border-t border-slate-200 bg-white">
            <div className="relative max-w-4xl mx-auto">
              <input 
                type="text" 
                placeholder="Ask ARIA to cross-reference CPGs with uploaded PDFs..."
                className="w-full bg-slate-50 border border-slate-300 rounded-xl py-3 pl-4 pr-12 text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500 transition-shadow placeholder-slate-400"
              />
              <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg transition-colors">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
