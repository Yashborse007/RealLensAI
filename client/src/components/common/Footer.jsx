import React from 'react';
import { ShieldCheck, Github, FileCheck2, Cpu } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950/90 py-10 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-8 border-b border-slate-800/60">
          
          {/* Brand info */}
          <div className="space-y-4 md:col-span-1">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-cyan-950 text-cyan-400 flex items-center justify-center border border-cyan-800/50">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="font-extrabold text-lg text-white font-['Outfit']">
                RealLens <span className="text-cyan-400">AI</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Next-generation multi-modal deepfake detection and media authenticity analysis portal for cybersecurity and digital forensics.
            </p>
          </div>

          {/* Quick Nav */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 font-['Outfit']">
              Platform Modules
            </h4>
            <ul className="space-y-2 text-xs text-slate-400">
              <li>
                <Link to="/dashboard" className="hover:text-cyan-400 transition-colors">
                  Overview Dashboard
                </Link>
              </li>
              <li>
                <Link to="/analyze" className="hover:text-cyan-400 transition-colors">
                  Media Analysis Lab
                </Link>
              </li>
              <li>
                <Link to="/history" className="hover:text-cyan-400 transition-colors">
                  Audit History Logs
                </Link>
              </li>
              <li>
                <Link to="/reports" className="hover:text-cyan-400 transition-colors">
                  Forensic PDF Reports
                </Link>
              </li>
            </ul>
          </div>

          {/* Forensic Pipeline Modalities */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 font-['Outfit']">
              Forensic Modalities
            </h4>
            <ul className="space-y-2 text-xs text-slate-400">
              <li className="flex items-center space-x-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                <span>Video Frame Consistency</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                <span>Audio Spectrogram Anomalies</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                <span>Image Noise Pattern Extraction</span>
              </li>
              <li className="flex items-center space-x-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>Metadata EXIF Verification</span>
              </li>
            </ul>
          </div>

          {/* Forensic Integrity & Compliance */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 font-['Outfit']">
              Forensic Integrity
            </h4>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-[11px] font-mono space-y-1.5 text-slate-400">
              <div className="flex justify-between">
                <span>Audit Trail:</span>
                <span className="text-cyan-300">SHA-256 Hashed</span>
              </div>
              <div className="flex justify-between">
                <span>PDF Reports:</span>
                <span className="text-indigo-300">Dual Executive & Tech</span>
              </div>
              <div className="flex justify-between">
                <span>Verification:</span>
                <span className="text-emerald-400">Multi-Modal Corroborated</span>
              </div>
            </div>
          </div>

        </div>

        {/* Bottom copyright line */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <p>&copy; 2026 RealLens AI. Information Technology Final-Year Project.</p>
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">Digital Forensics Framework v1.0</span>
            <span>&bull;</span>
            <span className="text-emerald-400 font-mono">Stage 1 Verified</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
