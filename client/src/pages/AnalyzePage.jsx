import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  UploadCloud,
  Image as ImageIcon,
  Video as VideoIcon,
  Mic as AudioIcon,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Info,
  Play,
  FileCheck,
  RefreshCw,
  Camera,
  CameraOff,
  Gauge,
  Activity,
} from "lucide-react";

import Card from "../components/common/Card";
import Button from "../components/common/Button";
import FileUploader from "../components/analysis/FileUploader";
import MediaPreview from "../components/analysis/MediaPreview";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import { useToast } from "../context/ToastContext";
import {
  uploadMediaFile,
  analyzeMediaFile,
  checkAiHealth,
  recordClientPerformance,
} from "../services/api";

const normalizePredictionLabel = (value) => {
  const raw = String(value || "").toLowerCase();
  if (raw.includes("real") || raw.includes("authentic")) return "Authentic";
  if (raw.includes("fake") || raw.includes("manipulated")) return "Manipulated";
  if (raw.includes("suspicious") || raw.includes("uncertain"))
    return "Uncertain";
  return "Awaiting result";
};

export default function AnalyzePage() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [activeTab, setActiveTab] = useState("image");
  const [selectedFile, setSelectedFile] = useState(null);

  const [uploadStatus, setUploadStatus] = useState("idle");
  const [processingStep, setProcessingStep] = useState("upload");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadData, setUploadData] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const [cameraStatus, setCameraStatus] = useState("idle");
  const [cameraError, setCameraError] = useState("");
  const [aiStatus, setAiStatus] = useState("checking");
  const [captureIntervalMs, setCaptureIntervalMs] = useState(2000);
  const [analysisState, setAnalysisState] = useState("Model unavailable");
  const [livePrediction, setLivePrediction] = useState("Awaiting result");
  const [liveConfidence, setLiveConfidence] = useState(0);
  const [liveFps, setLiveFps] = useState(0);
  const [liveLatencyMs, setLiveLatencyMs] = useState(0);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const captureTimerRef = useRef(null);
  const processingRef = useRef(false);
  const lastInferenceRef = useRef(0);
  const lastCaptureRef = useRef(0);

  useEffect(() => {
    let active = true;

    const checkHealth = async () => {
      try {
        const result = await checkAiHealth();
        if (!active) return;
        setAiStatus(result.status === "online" ? "online" : "offline");
        if (result.status !== "online") {
          setAnalysisState("Model unavailable");
        }
      } catch {
        if (active) {
          setAiStatus("offline");
          setAnalysisState("Model unavailable");
        }
      }
    };

    checkHealth();

    return () => {
      active = false;
      if (captureTimerRef.current) {
        clearInterval(captureTimerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (activeTab !== "webcam") {
      if (captureTimerRef.current) {
        clearInterval(captureTimerRef.current);
        captureTimerRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setCameraStatus("idle");
      setCameraError("");
    }
  }, [activeTab]);

  const handleTabChange = (type) => {
    setActiveTab(type);
    setSelectedFile(null);
    setUploadStatus("idle");
    setUploadProgress(0);
    setUploadData(null);
    setErrorMsg(null);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setUploadStatus("idle");
    setUploadProgress(0);
    setUploadData(null);
    setErrorMsg(null);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setUploadStatus("idle");
    setUploadProgress(0);
    setUploadData(null);
    setErrorMsg(null);
  };

  const handleUploadFile = async () => {
    if (!selectedFile) return;

    setProcessingStep("upload");
    setUploadStatus("uploading");
    setUploadProgress(0);
    setErrorMsg(null);

    try {
      const response = await uploadMediaFile(selectedFile, (percent) => {
        setUploadProgress(percent);
      });

      setUploadStatus("completed");
      setUploadData(response);
      notify("File uploaded and ready for analysis.", "success");
    } catch (err) {
      setUploadStatus("failed");
      setErrorMsg(
        err.message ||
          "Upload failed. Please check file format and server status.",
      );
    }
  };

  const handleStartAnalysis = async () => {
    if (!uploadData) return;

    try {
      setUploadStatus("uploading");
      setProcessingStep("analysis");
      setUploadProgress(0);
      const result = await analyzeMediaFile(uploadData.mediaId, () => {});
      navigate(
        `/analysis/${result.analysisId || result.id || uploadData.mediaId}`,
        {
          state: result,
        },
      );
    } catch (err) {
      setUploadStatus("failed");
      setErrorMsg(err.message || "Analysis failed. Please try again.");
      notify(err.message || "Analysis could not be completed.", "error");
    }
  };

  const stopCamera = () => {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraStatus("idle");
  };

  const startCamera = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraStatus("unsupported");
      setCameraError("This browser does not support webcam capture.");
      return;
    }

    try {
      setCameraStatus("requesting");
      setCameraError("");

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraStatus("ready");
      setAnalysisState(
        aiStatus === "online" ? "Analysis ready" : "Model unavailable",
      );
    } catch (error) {
      setCameraStatus("denied");
      setCameraError(
        error.name === "NotAllowedError"
          ? "Camera permission was denied. Please allow access and try again."
          : "Unable to start the camera. Please check hardware and permissions.",
      );
      setAnalysisState("Model unavailable");
    }
  };

  useEffect(() => {
    if (cameraStatus !== "ready") {
      if (captureTimerRef.current) {
        clearInterval(captureTimerRef.current);
        captureTimerRef.current = null;
      }
      return;
    }

    const runCaptureLoop = async () => {
      if (processingRef.current || !videoRef.current || aiStatus !== "online") {
        setAnalysisState("Model unavailable");
        return;
      }

      const video = videoRef.current;
      if (video.readyState < 2) return;

      const now = performance.now();
      if (now - lastCaptureRef.current < captureIntervalMs) return;
      lastCaptureRef.current = now;

      processingRef.current = true;
      setAnalysisState("Processing...");
      setLivePrediction("Processing...");

      const frameStart = performance.now();
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      try {
        const blob = await new Promise((resolve) => {
          canvas.toBlob(resolve, "image/jpeg", 0.9);
        });

        if (!blob) {
          throw new Error("Unable to capture webcam frame.");
        }

        const file = new File([blob], `webcam-frame-${Date.now()}.jpg`, {
          type: "image/jpeg",
        });

        const uploadResult = await uploadMediaFile(file, () => {});
        const analysisResult = await analyzeMediaFile(
          uploadResult.mediaId,
          () => {},
        );

        const confidenceValue = Number(
          analysisResult?.confidenceScore ??
            analysisResult?.confidence ??
            analysisResult?.prediction?.confidence ??
            0,
        );
        const predictionValue =
          analysisResult?.predictionLabel ||
          analysisResult?.result ||
          analysisResult?.prediction?.label ||
          "UNKNOWN";

        const normalizedPrediction = normalizePredictionLabel(predictionValue);
        const latency = performance.now() - frameStart;
        const priorInferenceTime =
          lastInferenceRef.current || performance.now();
        const fpsValue = lastInferenceRef.current
          ? 1000 / Math.max(1, performance.now() - priorInferenceTime)
          : 0;

        lastInferenceRef.current = performance.now();
        recordClientPerformance("webcam-frame-end-to-end", frameStart);
        setLivePrediction(normalizedPrediction);
        setLiveConfidence(confidenceValue);
        setLiveLatencyMs(Math.round(latency));
        setLiveFps(Math.round(fpsValue));
        setAnalysisState(
          confidenceValue < 0.6 ? "Low confidence" : "Analysis ready",
        );
      } catch (error) {
        recordClientPerformance("webcam-frame-end-to-end", frameStart);
        setLivePrediction("Model unavailable");
        setLiveConfidence(0);
        setAnalysisState("Model unavailable");
      } finally {
        processingRef.current = false;
      }
    };

    captureTimerRef.current = setInterval(
      runCaptureLoop,
      Math.max(800, captureIntervalMs),
    );

    return () => {
      if (captureTimerRef.current) {
        clearInterval(captureTimerRef.current);
        captureTimerRef.current = null;
      }
    };
  }, [cameraStatus, captureIntervalMs, aiStatus]);

  const renderWebcamPanel = () => (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-[1.5fr_0.9fr] gap-6">
        <Card hoverable={false} className="border-slate-800 overflow-hidden">
          <div className="relative h-[420px] bg-slate-950">
            {cameraStatus === "ready" ? (
              <>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="h-full w-full object-cover"
                />
                <div className="absolute inset-x-3 bottom-3 flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 backdrop-blur-sm">
                  <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
                    {analysisState}
                  </span>
                  <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-2 py-1 text-[10px] font-bold text-cyan-300">
                    {livePrediction}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-700 bg-slate-900 text-slate-400">
                  <CameraOff className="h-7 w-7" />
                </div>
                <div className="space-y-1">
                  <h3 className="text-lg font-bold text-white">
                    Webcam not active
                  </h3>
                  <p className="text-xs text-slate-400">
                    {cameraError ||
                      "Allow camera access to enable live prediction."}
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  icon={Camera}
                  onClick={startCamera}
                >
                  {cameraStatus === "requesting"
                    ? "Requesting Access..."
                    : "Start Camera"}
                </Button>
              </div>
            )}
          </div>
          <canvas ref={canvasRef} className="hidden" />
        </Card>

        <Card hoverable={false} className="border-slate-800 bg-slate-900/70">
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                  Model status
                </p>
                <p className="mt-2 text-lg font-bold text-white">
                  {aiStatus === "online" ? "Online" : "Offline"}
                </p>
              </div>
              <div
                className={`flex h-3 w-3 rounded-full ${
                  aiStatus === "online" ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
            </div>

            <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  Current prediction
                </span>
                <span className="text-xs font-semibold text-cyan-300">
                  {livePrediction}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Confidence</span>
                <span className="text-xs font-semibold text-white">
                  {liveConfidence
                    ? `${(liveConfidence * 100).toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">FPS</span>
                <span className="text-xs font-semibold text-white">
                  {liveFps ? `${liveFps} fps` : "N/A"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Latency</span>
                <span className="text-xs font-semibold text-white">
                  {liveLatencyMs ? `${liveLatencyMs} ms` : "N/A"}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
                Capture interval: {captureIntervalMs} ms
              </label>
              <input
                type="range"
                min="800"
                max="5000"
                step="200"
                value={captureIntervalMs}
                onChange={(event) =>
                  setCaptureIntervalMs(Number(event.target.value))
                }
                className="w-full accent-cyan-500"
              />
            </div>

            <div className="flex gap-3">
              <Button
                variant="primary"
                size="sm"
                icon={Camera}
                onClick={startCamera}
                disabled={
                  cameraStatus === "requesting" || cameraStatus === "ready"
                }
              >
                Start
              </Button>
              <Button
                variant="outline"
                size="sm"
                icon={CameraOff}
                onClick={stopCamera}
                disabled={cameraStatus !== "ready"}
              >
                Stop
              </Button>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-3 text-xs text-slate-300">
              <div className="mb-2 flex items-center gap-2 text-cyan-300">
                <Activity className="h-4 w-4" />
                <span>Session status</span>
              </div>
              <p>
                {aiStatus === "offline"
                  ? "Model unavailable. The AI service is offline, so live predictions will gracefully degrade."
                  : analysisState === "Processing..."
                    ? "Processing... measuring the latest frame against the detector."
                    : analysisState === "Low confidence"
                      ? "Low confidence. The model is active but the result is weak."
                      : analysisState === "Analysis ready"
                        ? "Analysis ready. Results reflect the latest measured frame."
                        : "Waiting for the next capture cycle."}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );

  return (
    <div className="space-y-8 animate-fade-in max-w-4xl mx-auto">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>Image, video and audio analysis</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-extrabold text-white font-['Outfit'] tracking-tight">
          Analyze media
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm max-w-xl mx-auto">
          Upload a media file to review the model result, evidence, and quality information.
          Some models may not be available for every file.
        </p>
      </div>

      <div className="flex items-center justify-center p-1.5 rounded-2xl bg-slate-900 border border-slate-800 max-w-lg mx-auto">
        <button
          type="button"
          onClick={() => handleTabChange("image")}
          aria-pressed={activeTab === "image"}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "image"
              ? "bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <ImageIcon className="w-4 h-4" />
          <span>Image</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange("video")}
          aria-pressed={activeTab === "video"}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "video"
              ? "bg-indigo-500 text-white shadow-md shadow-indigo-500/20"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <VideoIcon className="w-4 h-4" />
          <span>Video</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange("audio")}
          aria-pressed={activeTab === "audio"}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "audio"
              ? "bg-purple-500 text-white shadow-md shadow-purple-500/20"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <AudioIcon className="w-4 h-4" />
          <span>Audio</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange("webcam")}
          aria-pressed={activeTab === "webcam"}
          className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-bold transition-all ${
            activeTab === "webcam"
              ? "bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Camera className="w-4 h-4" />
          <span>Webcam</span>
        </button>
      </div>

      {uploadStatus === "failed" && errorMsg && (
        <ErrorMessage
          title={processingStep === "analysis" ? "Analysis failed" : "Upload failed"}
          message={errorMsg}
          onRetry={handleUploadFile}
          dismissable
          onDismiss={() => setErrorMsg(null)}
        />
      )}

      {activeTab === "webcam" ? (
        renderWebcamPanel()
      ) : !selectedFile ? (
        <div className="space-y-4">
          <FileUploader
            onFileSelect={handleFileSelect}
            activeType={activeTab}
            disabled={uploadStatus === "uploading"}
          />
        </div>
      ) : (
        <div className="space-y-6">
          <MediaPreview
            file={selectedFile}
            mediaType={activeTab}
            onRemove={handleRemoveFile}
            onAnalyze={handleUploadFile}
            isAnalyzing={uploadStatus === "uploading"}
          />

          {uploadStatus === "uploading" && (
            <Card hoverable={false} className="border-cyan-500/40 py-8">
              <div className="space-y-4 text-center">
                {processingStep === "analysis" ? (
                  <LoadingSpinner
                    label="Analyzing your media…"
                    sublabel="The detection models are reviewing available evidence."
                  />
                ) : (
                  <>
                    <LoadingSpinner
                      label={`Uploading your file (${uploadProgress}%)`}
                      sublabel="Keep this page open while the upload completes."
                    />
                    <div
                      className="mx-auto h-2 w-full max-w-md overflow-hidden rounded-full bg-slate-200"
                      role="progressbar"
                      aria-label="File upload progress"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={uploadProgress}
                    >
                      <div
                        style={{ width: `${uploadProgress}%` }}
                        className="h-full bg-blue-700 transition-[width] duration-200"
                      />
                    </div>
                  </>
                )}
              </div>
            </Card>
          )}

          {uploadStatus === "completed" && uploadData && (
            <Card
              hoverable={false}
              className="border-emerald-500/40 bg-emerald-950/20"
            >
              <div className="space-y-4">
                <div className="flex items-center space-x-3 text-emerald-400">
                  <CheckCircle2 className="w-6 h-6 shrink-0" />
                  <div>
                    <h3 className="font-bold text-base text-white font-['Outfit']">
                      Upload completed
                    </h3>
                    <p className="text-xs text-emerald-300/80">
                      File verified, sanitized, and registered in media
                      database.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/90 font-mono text-xs text-slate-300 space-y-2 border border-slate-800">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Media ID:</span>
                    <span className="text-cyan-400 font-bold">
                      {uploadData.mediaId}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Unique Filename:</span>
                    <span className="text-slate-200 truncate max-w-[240px]">
                      {uploadData.filename}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Modality:</span>
                    <span className="text-indigo-400 uppercase font-bold">
                      {uploadData.mediaType}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">MIME Type:</span>
                    <span>{uploadData.mimeType}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">File Size:</span>
                    <span>
                      {(uploadData.size / (1024 * 1024)).toFixed(2)} MB (
                      {uploadData.size} bytes)
                    </span>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button
                    variant="primary"
                    size="lg"
                    icon={Play}
                    onClick={handleStartAnalysis}
                    className="w-full sm:w-auto font-bold py-3.5"
                  >
                    Start Analysis
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
