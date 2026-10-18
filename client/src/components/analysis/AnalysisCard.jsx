import React from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Video as VideoIcon,
  Mic as AudioIcon,
  Image as ImageIcon,
  ArrowRight,
  Clock,
  HardDrive,
} from "lucide-react";
import StatusBadge from "../common/StatusBadge";

export default function AnalysisCard({ analysis }) {
  const {
    id,
    fileName,
    mediaType,
    fileSize,
    uploadedAt,
    result,
    confidenceScore,
    quality,
    qualityScore,
    qualityWarning,
    thumbnailUrl,
    flagsDetected = [],
  } = analysis;

  const formattedDate = new Date(uploadedAt).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="glass-card glass-card-hover rounded-2xl p-5 space-y-4 flex flex-col justify-between border border-slate-800/80">
      {/* Header Info */}
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0">
              {mediaType === "image" && (
                <ImageIcon className="w-5 h-5 text-cyan-400" />
              )}
              {mediaType === "video" && (
                <VideoIcon className="w-5 h-5 text-indigo-400" />
              )}
              {mediaType === "audio" && (
                <AudioIcon className="w-5 h-5 text-purple-400" />
              )}
            </div>

            <div className="overflow-hidden">
              <h4
                className="font-bold text-sm text-white font-['Outfit'] truncate"
                title={fileName}
              >
                {fileName}
              </h4>
              <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5 font-mono">
                <span className="flex items-center gap-1">
                  <HardDrive className="w-3 h-3 text-slate-500" />
                  {fileSize}
                </span>
                <span>&bull;</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {formattedDate}
                </span>
              </div>
            </div>
          </div>

          <StatusBadge status={result} size="sm" />
        </div>

        {/* Thumbnail or Media Graphic */}
        {thumbnailUrl ? (
          <div className="relative h-32 rounded-xl overflow-hidden bg-slate-950 border border-slate-800/80">
            <img
              src={thumbnailUrl}
              alt={fileName}
              className="w-full h-full object-cover opacity-80 hover:opacity-100 transition-opacity"
            />
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-slate-950/80 backdrop-blur-sm text-[10px] font-mono text-cyan-300 border border-slate-800">
              Score: {Math.round(confidenceScore * 100)}%
            </div>
          </div>
        ) : (
          <div className="h-24 rounded-xl bg-slate-950/60 border border-slate-800/60 p-3 flex flex-col justify-center space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
              Detection Flags ({flagsDetected.length})
            </span>
            {flagsDetected.length > 0 ? (
              <p className="text-xs text-rose-300 line-clamp-2">
                &bull; {flagsDetected.join(", ")}
              </p>
            ) : (
              <p className="text-xs text-emerald-400">
                &bull; No neural manipulation anomalies detected.
              </p>
            )}
          </div>
        )}

        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5 space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono uppercase tracking-[0.12em]">
            <span>Quality</span>
            <span
              className={`font-bold ${quality === "POOR" ? "text-amber-300" : quality === "FAIR" ? "text-yellow-300" : "text-emerald-300"}`}
            >
              {quality || "UNKNOWN"}
            </span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-slate-300">
            <span>Score</span>
            <span>
              {qualityScore === null || qualityScore === undefined
                ? "Not assessed"
                : `${Math.round(qualityScore * 100)}%`}
            </span>
          </div>
          {qualityWarning && (
            <p className="text-[10px] text-amber-300 leading-relaxed">
              {qualityWarning}
            </p>
          )}
        </div>
      </div>

      {/* Footer Link */}
      <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
        <span className="font-mono text-[11px] text-slate-500">ID: {id}</span>

        <Link
          to={`/analysis/${id}`}
          className="inline-flex items-center space-x-1.5 font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          <span>Forensic Details</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
