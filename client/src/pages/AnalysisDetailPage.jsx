import React, { useState, useEffect } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import {
  FileText,
  ArrowLeft,
  Download,
  Share2,
  Sparkles,
  Eye,
  FileCheck,
  Hash,
  Activity,
} from "lucide-react";

import Card from "../components/common/Card";
import Button from "../components/common/Button";
import StatusBadge from "../components/common/StatusBadge";
import ConfidenceGauge from "../components/analysis/ConfidenceGauge";
import Tooltip from "../components/common/Tooltip";
import { useToast } from "../context/ToastContext";
import SampleDataNotice from "../components/common/SampleDataNotice";
import PageSkeleton from "../components/common/PageSkeleton";
import Modal from "../components/common/Modal";
import { getAnalysisById, saveReportToDatabase } from "../services/api";
import { generateAnalysisReportPdf, getReportFileName } from "../utils/reportPdf";

const normalizeAnalysis = (raw = {}, fallbackId = "unknown") => {
  const rawPrediction = raw.prediction || raw.result || {};
  const prediction =
    typeof rawPrediction === "object"
      ? rawPrediction
      : { label: rawPrediction, confidence: raw.confidence };
  const label = String(
    prediction.label || raw.predictionLabel || raw.status || "UNKNOWN",
  ).toUpperCase();
  const score = Number(
    raw.confidenceScore ?? prediction.confidence ?? raw.confidence ?? 0,
  );
  const result =
    label === "REAL"
      ? "authentic"
      : label === "FAKE"
        ? "manipulated"
        : "suspicious";

  const evidence = Array.isArray(raw.evidence)
    ? raw.evidence.map((item) => {
        if (!item || typeof item !== "object") {
          return {
            type: "Forensic Evidence",
            description: String(item || "Signal evaluated"),
            severity: "low",
            metricValue: "Recorded",
          };
        }
        const desc =
          typeof item.description === "string" && item.description.trim()
            ? item.description
            : item.details
              ? summarizeEvidenceDetails(item.details)
              : typeof item.type === "string"
                ? `${item.type} evaluated`
                : "Forensic pattern evaluated";

        return {
          ...item,
          type: item.type || "Forensic Signal",
          description: desc,
          severity: item.severity || "low",
          metricValue: item.metricValue || "Recorded",
        };
      })
    : Array.isArray(raw.face_results)
      ? raw.face_results.map((face, index) => ({
          type: `Face output ${index + 1}`,
          severity: face.label === "FAKE" ? "high" : "low",
          description:
            face.label === "FAKE"
              ? "The model produced a stronger synthetic-likelihood signal in this face region."
              : "The face crop remained within the normal authenticity range for this detector.",
          metricValue: `${Math.round((face.confidence || 0) * 100)}% confidence`,
        }))
      : [];

  const sampleHeatmaps = Array.isArray(raw.sampleHeatmaps)
    ? raw.sampleHeatmaps
    : Array.isArray(raw.frame_predictions)
      ? raw.frame_predictions.slice(0, 3).map((frame, index) => {
          const timestamp = Number(frame.timestamp);
          const seconds = Number.isFinite(timestamp)
            ? timestamp
            : (index + 1) * 2;
          return {
            frameIndex: frame.frame_number || index + 1,
            timecode: `00:${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`,
            note:
              (frame.prediction || frame.label) === "FAKE"
                ? `Frame anomaly flagged by model${frame.confidence === undefined ? "" : ` · ${Math.round(frame.confidence * 100)}% confidence`}`
                : "Frame remained stable",
          };
        })
      : [];

  const fileSizeRaw =
    typeof raw.fileSize === "number" ? raw.fileSize : Number(raw.size || 0);

  return {
    id: raw.id || raw.analysisId || raw.mediaId || fallbackId,
    mediaId: raw.mediaId || raw.analysisId || fallbackId,
    fileName:
      raw.fileName || raw.originalName || raw.filename || `media-${fallbackId}`,
    mediaType: raw.mediaType || "image",
    fileSize: raw.fileSize || `${fileSizeRaw} B`,
    mimeType: raw.mimeType || "application/octet-stream",
    uploadedAt: raw.uploadedAt || new Date().toISOString(),
    processedAt: raw.processedAt || new Date().toISOString(),
    status: raw.status || "completed",
    result,
    confidenceScore: Number.isFinite(score)
      ? Math.min(Math.max(score, 0), 1)
      : 0,
    predictionLabel: label,
    metadata: raw.metadata || {
      cameraModel: "No embedded EXIF metadata",
      encoding: "AIDE inference pipeline",
      hashSHA256: "not generated in gateway",
      software: raw.model || "AIDE",
    },
    evidence,
    sampleHeatmaps,
    modelVersion: raw.modelVersion || raw.model || "AIDE-CNN-v1.0",
    processingTimeMs: raw.processingTimeMs || raw.processing_time_ms || 0,
    facesDetected: raw.facesDetected || raw.faces_detected || 0,
    framesAnalyzed: raw.framesAnalyzed || raw.frames_analyzed || 0,
    quality:
      (typeof raw.quality === "object"
        ? raw.quality.status
        : raw.quality) ||
      raw.qualityStatus ||
      raw.inputQuality?.status ||
      "UNKNOWN",
    qualityScore: (() => {
      const value =
        raw.qualityScore ??
        raw.quality_score ??
        raw.quality?.score ??
        raw.quality?.quality_score ??
        raw.inputQuality?.qualityScore ??
        raw.input_quality?.quality_score;
      return value === null || value === undefined ? null : Number(value);
    })(),
    qualityWarning:
      raw.qualityWarning ||
      raw.quality?.warning ||
      raw.inputQuality?.warning ||
      raw.qualityDetails?.warning ||
      "",
    qualityDetails:
      raw.qualityDetails ||
      raw.quality?.details ||
      raw.inputQuality ||
      raw.input_quality ||
      {},
    modalities: raw.modalities || raw.modalityScores || {},
    timestamps: raw.timestamps || {},
    processing: raw.processing || {},
    modelVersions: raw.model_versions || raw.modelVersions || {},
    message: raw.message || null,
    threshold: raw.threshold || 0.5,
    model: raw.model || "AIDE",
    duration: raw.duration || (raw.mediaType === "video" ? "00:00:00" : "N/A"),
  };
};

const summarizeEvidenceDetails = (details) => {
  if (Array.isArray(details)) {
    const samples = details.slice(0, 5).map((item) => {
      const frame = item?.frame_number ?? item?.frameIndex ?? "?";
      const time = item?.timestamp;
      const label = item?.prediction || item?.label || "output";
      const confidence =
        item?.confidence === null || item?.confidence === undefined
          ? ""
          : ` (${Math.round(Number(item.confidence) * 100)}%)`;
      return `frame ${frame}${time === undefined ? "" : ` @ ${time}s`}: ${label}${confidence}`;
    });
    return `${details.length} recorded outputs${samples.length ? ` · ${samples.join("; ")}` : ""}`;
  }
  if (details && typeof details === "object") return JSON.stringify(details);
  return String(details);
};

export default function AnalysisDetailPage() {
  const { id } = useParams();
  const { state } = useLocation();
  const { notify } = useToast();
  const [analysis, setAnalysis] = useState(
    state ? normalizeAnalysis(state, id) : null,
  );
  const [loading, setLoading] = useState(!state);
  const [analysisError, setAnalysisError] = useState(null);
  const [isSampleData, setIsSampleData] = useState(Boolean(state?.isSampleData));
  const [showReportModal, setShowReportModal] = useState(false);

  useEffect(() => {
    if (state) {
      setAnalysis(normalizeAnalysis(state, id));
      setIsSampleData(Boolean(state.isSampleData));
      setAnalysisError(null);
      setLoading(false);
      return;
    }

    const fetchDetails = async () => {
      setLoading(true);
      setAnalysisError(null);
      try {
        const data = await getAnalysisById(id);
        setAnalysis(normalizeAnalysis(data, id));
        setIsSampleData(Boolean(data?.isSampleData));
      } catch (error) {
        setAnalysis(null);
        setAnalysisError(error?.message || "Unable to load this analysis.");
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [id, state]);

  if (loading) {
    return (
      <div className="py-20 flex justify-center">
        <PageSkeleton cards={3} rows={4} />
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-white">
          {analysisError ? "Analysis unavailable" : "Analysis not found"}
        </h2>
        <p className="text-xs text-slate-400">
          {analysisError ||
            "This analysis may have been removed or you may not have access to it."}
        </p>
        <Link to="/dashboard">
          <Button variant="outline" size="sm" icon={ArrowLeft}>
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  const {
    fileName,
    mediaType,
    fileSize,
    mimeType,
    result,
    confidenceScore,
    metadata = {},
    evidence = [],
    sampleHeatmaps = [],
    modelVersion,
    processingTimeMs,
    facesDetected,
    framesAnalyzed,
    message,
    quality,
    qualityScore,
    qualityWarning,
    qualityDetails = {},
    modalities = {},
    timestamps = {},
    processing = {},
    modelVersions = {},
  } = analysis;

  const confidencePercent = Math.round(confidenceScore * 100);
  const summaryTitle =
    result === "authentic"
      ? "Likely authentic"
      : result === "manipulated"
        ? "Potentially manipulated"
        : "Needs further review";

  const explanationEngine = (() => {
    const firstItem = Array.isArray(evidence) && evidence.length > 0 ? evidence[0] : null;
    const descText =
      firstItem?.description ||
      (typeof firstItem?.details === "string" ? firstItem.details : null) ||
      firstItem?.type ||
      "anomaly indicators";

    const techSignal =
      firstItem
        ? `${firstItem.type || "Forensic Signal"}; confidence = ${confidencePercent}%`
        : `No strong anomaly signal detected; confidence = ${confidencePercent}%`;

    const simpleSignal =
      firstItem
        ? `The system noticed ${String(descText).toLowerCase()}. This contributed to the prediction.`
        : "The model did not find a strong anomaly signal in the media it examined. This kept the prediction conservative.";

    const conclusion =
      result === "authentic"
        ? `The model classified this media as likely authentic with ${confidencePercent}% confidence.`
        : result === "manipulated"
          ? `The model classified this media as potentially manipulated with ${confidencePercent}% confidence.`
          : `The model produced an uncertain result with ${confidencePercent}% confidence, so this should be reviewed by a person.`;

    return {
      technical: techSignal,
      simple: simpleSignal,
      conclusion,
    };
  })();

  const summaryText =
    message ||
    (result === "authentic"
      ? "The model classified this media as likely authentic. Automated results are not a guarantee of authenticity."
      : "The model flagged a possible manipulation pattern. This does not prove a deepfake by itself; review the evidence and context.");

  return (
    <div className="space-y-8 animate-fade-in">
      {isSampleData && <SampleDataNotice />}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div className="flex items-center space-x-3">
          <Link
            to="/history"
            className="p-2.5 rounded-xl bg-slate-900 text-slate-400 hover:text-white border border-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <span className="font-mono text-xs text-cyan-400">
                Case ID: {id}
              </span>
              <StatusBadge status={result} size="sm" />
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 shadow-sm">
                {String(mediaType || "Media").toUpperCase()} Confidence: {Math.round(confidenceScore * 100)}%
              </span>
            </div>
            <h1 className="text-2xl font-extrabold text-white font-['Outfit'] truncate max-w-lg mt-0.5">
              {fileName}
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="secondary"
            size="md"
            icon={Share2}
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(window.location.href);
                notify("Analysis link copied to clipboard.", "success");
              } catch {
                notify("Clipboard access was denied. Copy the page URL from your browser.", "error");
              }
            }}
          >
            Share
          </Button>
          <Button
            variant="primary"
            size="md"
            icon={FileText}
            onClick={() => setShowReportModal(true)}
          >
            Download report
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <ConfidenceGauge
              score={confidenceScore}
              result={result}
              showLabel
            />

            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
              <div className="space-y-1">
                <Tooltip text="This is the model's result, not a definitive authenticity guarantee.">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 font-mono">
                    Model result
                  </span>
                </Tooltip>
                <h3 className="text-xl font-black text-white font-['Outfit']">
                  {summaryTitle}
                </h3>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                {summaryText}
              </p>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-2 text-[11px] text-slate-300">
                <div className="flex items-center justify-between">
                  <Tooltip text="Input quality can affect model performance; it is shown separately from the prediction.">
                    <span className="text-slate-400">Media quality</span>
                  </Tooltip>
                  <span
                    className={`font-bold ${quality === "POOR" ? "text-amber-300" : quality === "FAIR" ? "text-yellow-300" : "text-emerald-300"}`}
                  >
                    {quality || "UNKNOWN"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Quality score</span>
                  <span className="text-white">
                    {qualityScore === null
                      ? "Not assessed"
                      : `${Math.round(qualityScore * 100)}%`}
                  </span>
                </div>
                {qualityWarning && (
                  <p className="text-[10px] text-amber-300">{qualityWarning}</p>
                )}
              </div>

              <div className="pt-2 border-t border-slate-800 flex flex-col gap-1 text-xs font-mono text-slate-400">
                <div className="flex justify-between">
                  <span>Model Pipeline: {modelVersion}</span>
                  <span className="text-cyan-400">
                    Confidence: {Math.round(confidenceScore * 100)}%
                  </span>
                </div>
                {analysis.processing?.fusion?.decision_margin !== undefined && (
                  <div className="flex justify-between text-[11px] text-slate-500">
                    <span>Decision Margin (from 50% threshold):</span>
                    <span>{(Number(analysis.processing.fusion.decision_margin) * 100).toFixed(2)}%</span>
                  </div>
                )}
                {analysis.ground_truth && (
                  <div className="flex justify-between text-[11px] text-amber-400/90 pt-1 border-t border-slate-800/60">
                    <span>Known Ground Truth: {analysis.ground_truth}</span>
                    <span className="font-bold">Evaluation: {analysis.evaluation_outcome || "N/A"}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <Card
            title="How the result was produced"
            subtitle="The model signal, how it was combined, and a plain-language explanation."
            icon={Sparkles}
            className="border-slate-800"
          >
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  Technical Result
                </p>
                <p className="text-sm text-white font-medium">
                  {explanationEngine.technical}
                </p>
              </div>

              <div className="text-center text-slate-500 text-xs">↓</div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  Explanation Engine
                </p>
                <p className="text-sm text-slate-200 leading-relaxed">
                  The model weighs several signals together and converts them
                  into one classification score.
                </p>
              </div>

              <div className="text-center text-slate-500 text-xs">↓</div>

              <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-300">
                  Simple Language
                </p>
                <p className="text-sm text-cyan-50 leading-relaxed">
                  {explanationEngine.simple}
                </p>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <p className="text-xs text-slate-300 leading-relaxed">
                  {explanationEngine.conclusion}
                </p>
              </div>
            </div>
          </Card>

          <Card
            title="Evidence"
            subtitle="Signals reported by the models that ran for this media."
            icon={Sparkles}
            className="border-slate-800"
          >
            <div className="space-y-4">
              {evidence.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/80 p-6 text-sm text-slate-400 text-center">
                  No explicit evidence was returned by the available models for
                  this file.
                </div>
              ) : (
                evidence.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`w-2 h-2 rounded-full ${item.severity === "high" ? "bg-rose-500" : item.severity === "medium" ? "bg-amber-500" : "bg-cyan-500"}`}
                        />
                        <h4 className="font-bold text-sm text-white font-['Outfit']">
                          {item.type}
                        </h4>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${item.severity === "high" ? "badge-rose" : item.severity === "medium" ? "badge-amber" : "badge-cyan"}`}
                      >
                        {item.severity} Severity
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {item.description ||
                        (item.details
                          ? summarizeEvidenceDetails(item.details)
                          : "No additional detail was returned.")}
                    </p>
                    <div className="pt-1 flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span>Metric output:</span>
                      <span className="text-cyan-300">{item.metricValue}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card
            title="Modality Scores & Fusion"
            subtitle="Every available raw modality output and its role in the final decision"
            icon={Activity}
            className="border-slate-800"
          >
            <div className="space-y-3">
              {["spatial", "temporal", "frequency", "audio"].map((name) => {
                const modality = modalities[name] || {};
                const score = Number(modality.score);
                const hasScore =
                  modality.score !== null &&
                  modality.score !== undefined &&
                  Number.isFinite(score);
                return (
                  <div
                    key={name}
                    className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h4 className="text-sm font-bold text-white capitalize">
                        {name}
                      </h4>
                      <span className="text-[10px] font-mono uppercase text-cyan-300">
                        {modality.status || "NOT_REPORTED"}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <span className="text-slate-400">Raw score</span>
                      <span className="text-right text-white font-mono">
                        {hasScore ? score.toFixed(4) : "Not available"}
                      </span>
                      <span className="text-slate-400">Score meaning</span>
                      <span className="text-right text-slate-200">
                        {modality.score_type || "Not reported"}
                      </span>
                      <span className="text-slate-400">Fusion role</span>
                      <span className="text-right text-slate-200">
                        {modality.included_in_fusion
                          ? `Included (weight ${Number(modality.normalized_fusion_weight ?? modality.fusion_weight ?? 0).toFixed(3)}${modality.weighted_contribution === undefined ? "" : `; contribution ${Number(modality.weighted_contribution).toFixed(4)}`})`
                          : "Not included"}
                      </span>
                      {modality.label && (
                        <>
                          <span className="text-slate-400">Modality label</span>
                          <span className="text-right text-white">
                            {modality.label}
                            {modality.confidence !== null &&
                            modality.confidence !== undefined
                              ? ` · ${Math.round(modality.confidence * 100)}%`
                              : ""}
                          </span>
                        </>
                      )}
                    </div>
                    {(modality.fusion_message || modality.message) && (
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        {modality.fusion_message || modality.message}
                      </p>
                    )}
                  </div>
                );
              })}
              {processing.fusion && (
                <div className="rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-4 space-y-2 text-xs">
                  <h4 className="font-bold text-indigo-200">Final fusion</h4>
                  <p className="text-slate-300">
                    Method: {processing.fusion.method || "Not reported"} ·
                    threshold:{" "}
                    {Number(processing.fusion.threshold ?? 0.5).toFixed(2)}
                  </p>
                  <p className="text-slate-300">
                    Fused fake probability:{" "}
                    {processing.fusion.fake_probability === null ||
                    processing.fusion.fake_probability === undefined
                      ? "Not available"
                      : `${(processing.fusion.fake_probability * 100).toFixed(2)}%`}
                  </p>
                  <p className="text-[11px] text-amber-200">
                    Confidence:{" "}
                    {processing.fusion.confidence_calibration
                      ?.statistically_calibrated
                      ? "statistically calibrated"
                      : "decision-margin estimate; not statistically calibrated"}
                  </p>
                </div>
              )}
            </div>
          </Card>

          <Card
            title="Pipeline Trace"
            subtitle="Module execution, unavailable modalities, and model versions"
            icon={Activity}
            className="border-slate-800"
          >
            <div className="space-y-2 text-xs">
              {Object.entries(processing.modules || {}).map(([name, module]) => (
                <div
                  key={name}
                  className="flex justify-between gap-4 border-b border-slate-800 py-2"
                >
                  <span className="text-slate-300 capitalize">
                    {name.replace(/_/g, " ")}
                  </span>
                  <span className="text-right font-mono text-cyan-300">
                    {module.status || "UNKNOWN"}
                    {module.duration_ms !== undefined
                      ? ` · ${module.duration_ms} ms`
                      : ""}
                  </span>
                </div>
              ))}
              {Object.entries(modelVersions).map(([name, version]) => (
                <div
                  key={`version-${name}`}
                  className="flex justify-between gap-4 py-1 text-[11px]"
                >
                  <span className="text-slate-500 capitalize">
                    {name} model
                  </span>
                  <span className="text-slate-300">{version}</span>
                </div>
              ))}
              {timestamps.started_at && (
                <p className="pt-2 text-[10px] text-slate-500 font-mono">
                  Started {timestamps.started_at}
                  {timestamps.completed_at
                    ? ` · completed ${timestamps.completed_at}`
                    : ""}
                </p>
              )}
            </div>
          </Card>

          {sampleHeatmaps.length > 0 && (
            <Card
              title="Video frame evidence"
              subtitle="Sampled frames returned by the video detector"
              icon={Eye}
              className="border-slate-800"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {sampleHeatmaps.map((hf, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs"
                  >
                    <div className="h-28 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center relative overflow-hidden">
                      <div className="absolute inset-0 bg-gradient-to-tr from-rose-500/20 via-transparent to-cyan-500/20" />
                      <span className="font-mono text-slate-400 text-[11px] z-10">
                        Frame #{hf.frameIndex}
                      </span>
                    </div>
                    <div className="flex justify-between font-mono text-[10px] text-slate-400">
                      <span>Timecode:</span>
                      <span className="text-cyan-300">{hf.timecode}</span>
                    </div>
                    <p className="text-[11px] text-rose-300 truncate">
                      {hf.note}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card
            title="File and analysis details"
            subtitle="Metadata and processing summary"
            icon={Hash}
            className="border-slate-800"
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">File Name:</span>
                <span className="text-slate-200 truncate max-w-[140px]">
                  {fileName}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">File Size:</span>
                <span className="text-slate-200">{fileSize}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">MIME Type:</span>
                <span className="text-slate-200">{mimeType}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">Modality:</span>
                <span className="text-slate-200">{mediaType}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">Faces / Frames:</span>
                <span className="text-slate-200">
                  {facesDetected || framesAnalyzed || 0}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">Quality:</span>
                <span
                  className={`text-slate-200 ${quality === "POOR" ? "text-amber-300" : quality === "FAIR" ? "text-yellow-300" : "text-emerald-300"}`}
                >
                  {quality || "UNKNOWN"}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-500">Runtime:</span>
                <span className="text-slate-200">
                  {processingTimeMs ? `${processingTimeMs} ms` : "N/A"}
                </span>
              </div>
              <div className="pt-2 space-y-1">
                <span className="text-slate-500 text-[10px] block uppercase">
                  Model:
                </span>
                <div className="p-2 rounded-lg bg-slate-950 text-[10px] text-cyan-400 break-all border border-slate-800">
                  {metadata.software || modelVersion}
                </div>
              </div>
            </div>
          </Card>

          <Card
            title="PDF report"
            subtitle="Summary of this analysis"
            icon={FileCheck}
            className="border-slate-800"
          >
            <div className="space-y-4">
              <p className="text-xs text-slate-400 leading-relaxed">
                This report summarizes the current model verdict, confidence
                score, and evidence context for the uploaded media.
              </p>
              <Button
                variant="primary"
                size="md"
                icon={Download}
                onClick={() => setShowReportModal(true)}
                className="w-full"
              >
                Download PDF
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <Modal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        title="Analysis report"
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowReportModal(false)}
            >
              Close
            </Button>
            <Button
              variant="outline"
              size="sm"
              icon={Eye}
              onClick={() => {
                try {
                  const result = generateAnalysisReportPdf(analysis, { autoDownload: false });
                  if (result.url) {
                    window.open(result.url, "_blank");
                  }
                  if (result.fileName) {
                    saveReportToDatabase(analysis.id || analysis.mediaId, result.fileName, result.base64);
                  }
                  notify(`Opening ${result.fileName} in viewer.`, "info");
                } catch (err) {
                  notify(err?.message || "Failed to open report PDF.", "error");
                }
              }}
            >
              Open PDF
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={Download}
              onClick={() => {
                try {
                  const result = generateAnalysisReportPdf(analysis, { autoDownload: true });
                  if (result.fileName) {
                    saveReportToDatabase(analysis.id || analysis.mediaId, result.fileName, result.base64);
                  }
                  notify(`Downloaded: ${result.fileName}`, "success");
                  setShowReportModal(false);
                } catch (err) {
                  notify(err?.message || "Failed to generate report PDF.", "error");
                }
              }}
            >
              Download PDF
            </Button>
          </>
        }
      >
        <div className="space-y-4 font-mono text-xs">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <h4 className="font-bold text-sm text-cyan-300 font-['Outfit']">
              RealLens AI Forensic Audit Document
            </h4>
            <p className="text-slate-400 text-[11px]">
              Document ID: CERT-{id.toUpperCase()}-2026
            </p>
          </div>

          <div className="space-y-2 text-slate-300">
            <p>
              <strong>Case File:</strong> {fileName}
            </p>
            <p>
              <strong>Result:</strong> {result.toUpperCase()}
            </p>
            <p>
              <strong>Model Confidence Score:</strong>{" "}
              {Math.round(confidenceScore * 100)}% (Uncalibrated distance from threshold)
            </p>
            <p>
              <strong>Authenticity Verification:</strong> Not established by model prediction alone
            </p>
            <p>
              <strong>Media Quality:</strong> {quality || "UNKNOWN"} (
              {qualityScore === null
                ? "not assessed"
                : `${Math.round(qualityScore * 100)}%`})
            </p>
            {qualityWarning && (
              <p>
                <strong>Quality Warning:</strong> {qualityWarning}
              </p>
            )}
            <p>
              <strong>Timestamp:</strong> {new Date().toUTCString()}
            </p>
          </div>

          <p className="text-slate-500 text-[11px]">
            This report contains model output and evidence summary context for
            chain-of-custody review. Poor media quality does not automatically
            mean the media is fake.
          </p>
        </div>
      </Modal>
    </div>
  );
}
