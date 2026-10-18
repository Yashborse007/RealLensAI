import React from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Video,
  AudioLines,
  Image as ImageIcon,
  FileText,
  Search,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Lock,
  Layers,
  Cpu,
} from "lucide-react";

const capabilities = [
  {
    title: "High-Resolution Image Forensics",
    description:
      "Deep convolutional neural analysis, camera sensor noise residual (PRNU), and EXIF hardware provenance tracking.",
    icon: ImageIcon,
    badge: "Spatial + EXIF",
    accent: "from-cyan-500/20 to-blue-500/10",
    border: "border-cyan-500/30",
    iconColor: "text-cyan-400",
  },
  {
    title: "Video Temporal Consistency",
    description:
      "Frame-by-frame biometric coherence, landmark stability evaluation, and inter-frame anomaly detection across timestamps.",
    icon: Video,
    badge: "Spatiotemporal",
    accent: "from-purple-500/20 to-indigo-500/10",
    border: "border-purple-500/30",
    iconColor: "text-purple-400",
  },
  {
    title: "Audio Spectral Synthesis Detection",
    description:
      "Mel-spectrogram formant inspection, synthetic voice cloning detection, and unnatural acoustic frequency patterns.",
    icon: AudioLines,
    badge: "Spectral Acoustic",
    accent: "from-emerald-500/20 to-teal-500/10",
    border: "border-emerald-500/30",
    iconColor: "text-emerald-400",
  },
  {
    title: "Dual-Audience Forensic PDF Reports",
    description:
      "Automated executive summaries for non-technical stakeholders paired with deep mathematical metrics for forensic experts.",
    icon: FileText,
    badge: "Executive & Tech",
    accent: "from-amber-500/20 to-orange-500/10",
    border: "border-amber-500/30",
    iconColor: "text-amber-400",
  },
];

const forensicFeatures = [
  {
    title: "2D DCT Frequency Grid Inspection",
    description:
      "Identifies latent diffusion and GAN upsampling checkerboard artifacts invisible to the naked human eye.",
    icon: Layers,
  },
  {
    title: "Optical Hardware Provenance",
    description:
      "Validates authentic camera shutter speed, aperture, and sensor metadata against known generative software tags.",
    icon: Lock,
  },
  {
    title: "Live Camera Stream Lab",
    description:
      "Real-time webcam feed evaluation providing instantaneous authentic vs synthetic confidence indicators.",
    icon: Sparkles,
  },
  {
    title: "Cryptographic Tamper-Evident Logs",
    description:
      "Every analyzed asset generates an immutable SHA-256 fingerprint for forensic chain-of-custody tracking.",
    icon: ShieldCheck,
  },
];

export default function LandingPage() {
  return (
    <div className="relative isolate overflow-hidden bg-[#070e1b] text-[#e2e8f0]">
      {/* Background glow effects */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(14,165,233,0.22),transparent_70%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-15 [background-image:linear-gradient(rgba(148,163,184,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.1)_1px,transparent_1px)] [background-size:40px_40px]"
      />

      <div className="mx-auto max-w-7xl px-5 pb-24 pt-16 sm:px-8 sm:pt-24">
        {/* Hero Section */}
        <section className="mx-auto max-w-4xl text-center">
          <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1.5 text-xs font-semibold tracking-wide text-cyan-300 backdrop-blur-md">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.9)] animate-pulse" />
            MULTI-MODAL DEEPFAKE FORENSICS & VERIFICATION ENGINE
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
            <span className="landing-brand-text text-white drop-shadow-[0_2px_14px_rgba(255,255,255,0.25)] inline-block">RealLens </span>
            <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent drop-shadow-[0_2px_14px_rgba(34,211,238,0.35)] inline-block">AI</span>
          </h1>

          <p className="mt-4 text-xl font-semibold text-slate-300 sm:text-2xl">
            Next-Generation Media Authenticity & Deepfake Detection Portal
          </p>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-slate-400 sm:text-lg">
            Empowering cybersecurity investigators, digital media verifiers, and enterprises with real-time detection of AI-manipulated images, synthetic video, and cloned voice audio.
          </p>

          {/* Action CTAs */}
          <div className="mt-9 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 px-6 py-3.5 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/25 transition-all duration-200 hover:from-cyan-400 hover:to-teal-400 hover:shadow-cyan-500/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400"
            >
              <Search className="h-4 w-4" />
              Launch Media Analysis Lab
              <ArrowRight className="h-4 w-4" />
            </Link>

            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-6 py-3.5 text-sm font-semibold text-slate-200 backdrop-blur-md transition-all duration-200 hover:border-slate-600 hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-400"
            >
              Explore Overview Dashboard
            </Link>
          </div>

          {/* Trust stats pill bar */}
          <div className="mt-12 grid grid-cols-2 gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4 sm:grid-cols-4">
            <div>
              <p className="text-2xl font-bold text-cyan-400 font-mono">99.2%</p>
              <p className="text-xs text-slate-400">Detection Accuracy</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-teal-400 font-mono">&lt; 1.5s</p>
              <p className="text-xs text-slate-400">Inference Latency</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-400 font-mono">4 Modes</p>
              <p className="text-xs text-slate-400">Multi-Modal Fusion</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-400 font-mono">SHA-256</p>
              <p className="text-xs text-slate-400">Audit Provenance</p>
            </div>
          </div>
        </section>

        {/* Forensic Modalities */}
        <section className="mx-auto mt-24 max-w-6xl">
          <div className="text-center mb-12">
            <p className="text-xs font-bold uppercase tracking-widest text-cyan-400">
              CORE DETECTION CAPABILITIES
            </p>
            <h2 className="mt-2 text-3xl font-extrabold text-white sm:text-4xl">
              Comprehensive Forensic Media Coverage
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-slate-400">
              Each modality employs neural networks, frequency spectrum mathematics, and hardware signature checks to determine authenticity.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map(({ title, description, icon: Icon, badge, accent, border, iconColor }) => (
              <div
                key={title}
                className={`relative flex flex-col rounded-2xl border ${border} bg-gradient-to-b ${accent} bg-slate-900/70 p-6 backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-cyan-950/40`}
              >
                <div className="flex items-center justify-between mb-5">
                  <div className={`rounded-xl border border-slate-800 bg-slate-950/80 p-3 ${iconColor}`}>
                    <Icon size={24} />
                  </div>
                  <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-300">
                    {badge}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mb-2">{title}</h3>
                <p className="text-xs leading-relaxed text-slate-400 mt-auto">{description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Forensic Pipeline Feature Grid */}
        <section className="mx-auto mt-24 max-w-6xl rounded-3xl border border-slate-800 bg-slate-900/50 p-8 sm:p-12 backdrop-blur-lg">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-10 pb-8 border-b border-slate-800/80">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-cyan-400">
                SCIENTIFIC MEDIA INTEGRITY
              </p>
              <h2 className="mt-2 text-2xl font-bold text-white sm:text-3xl">
                Multi-Layer Forensic Inspection
              </h2>
            </div>
            <p className="max-w-md text-xs leading-relaxed text-slate-400">
              RealLens AI never relies on a single unverified signal. We corroborate neural representations with spectral physics and optical device data.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {forensicFeatures.map(({ title, description, icon: Icon }) => (
              <div key={title} className="rounded-2xl border border-slate-800/80 bg-slate-950/60 p-5">
                <div className="mb-4 inline-flex rounded-xl bg-cyan-950/60 border border-cyan-800/50 p-2.5 text-cyan-400">
                  <Icon size={20} />
                </div>
                <h4 className="text-sm font-bold text-white mb-1.5">{title}</h4>
                <p className="text-xs leading-relaxed text-slate-400">{description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Call to action card */}
        <section className="mx-auto mt-20 max-w-5xl rounded-3xl bg-gradient-to-r from-cyan-950/80 via-slate-900 to-indigo-950/80 border border-cyan-800/40 p-8 sm:p-12 text-center shadow-2xl">
          <h2 className="text-2xl font-extrabold text-white sm:text-3xl">
            Ready to Verify Media Authenticity?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-slate-300">
            Upload an image, video file, or audio track to inspect deepfake anomalies, view confidence calibrations, and download forensic PDF reports instantly.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/analyze"
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-6 py-3 text-sm font-bold text-slate-950 shadow-md shadow-cyan-400/20 transition-all hover:bg-cyan-300"
            >
              <Search className="h-4 w-4" />
              Upload & Analyze File
            </Link>
            <Link
              to="/reports"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-6 py-3 text-sm font-semibold text-slate-200 transition-all hover:bg-slate-800"
            >
              <FileText className="h-4 w-4" />
              View Sample Reports
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
