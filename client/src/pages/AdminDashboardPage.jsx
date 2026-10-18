import React, { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  LineChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock3,
  Cpu,
  FileText,
  Layers3,
  ShieldCheck,
  Users,
  Video,
  Image as ImageIcon,
  Mic,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import {
  getAdminOverview,
  getAdminUsers,
  getAdminModels,
} from "../services/api";
import PageSkeleton from "../components/common/PageSkeleton";
import ErrorMessage from "../components/common/ErrorMessage";

const chartColors = ["#22d3ee", "#34d399", "#f59e0b", "#f472b6", "#818cf8"];

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overview, setOverview] = useState({
    stats: {},
    charts: {
      analysisVolume: [],
      predictionDistribution: [],
      mediaTypeDistribution: [],
      processingTime: [],
    },
    users: [],
    recentAnalyses: [],
  });
  const [models, setModels] = useState([]);

  const loadAdminData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [overviewRes, usersRes, modelsRes] = await Promise.all([
        getAdminOverview(),
        getAdminUsers(),
        getAdminModels(),
      ]);

      setOverview({
        stats: overviewRes?.stats || {},
        charts: overviewRes?.charts || {
          analysisVolume: [],
          predictionDistribution: [],
          mediaTypeDistribution: [],
          processingTime: [],
        },
        users: overviewRes?.users || usersRes?.data || [],
        recentAnalyses: overviewRes?.recentAnalyses || [],
      });
      setModels(modelsRes?.data || []);
    } catch (err) {
      setError(err?.message || "Unable to load admin dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const statCards = useMemo(
    () => [
      {
        label: "Total Users",
        value: overview.stats.totalUsers ?? 0,
        icon: Users,
        accent: "cyan",
      },
      {
        label: "Total Analyses",
        value: overview.stats.totalAnalyses ?? 0,
        icon: Activity,
        accent: "indigo",
      },
      {
        label: "Likely authentic",
        value: overview.stats.realPredictions ?? 0,
        icon: CheckCircle2,
        accent: "emerald",
      },
      {
        label: "Potentially manipulated",
        value: overview.stats.fakePredictions ?? 0,
        icon: AlertTriangle,
        accent: "rose",
      },
      {
        label: "Uncertain results",
        value: overview.stats.uncertainPredictions ?? 0,
        icon: ShieldCheck,
        accent: "amber",
      },
      {
        label: "Image Analyses",
        value: overview.stats.imageAnalyses ?? 0,
        icon: ImageIcon,
        accent: "cyan",
      },
      {
        label: "Video Analyses",
        value: overview.stats.videoAnalyses ?? 0,
        icon: Video,
        accent: "violet",
      },
      {
        label: "Audio Analyses",
        value: overview.stats.audioAnalyses ?? 0,
        icon: Mic,
        accent: "purple",
      },
      {
        label: "Failed Analyses",
        value: overview.stats.failedAnalyses ?? 0,
        icon: FileText,
        accent: "red",
      },
      {
        label: "Avg Processing Time",
        value: `${overview.stats.averageProcessingTimeMs ?? 0} ms`,
        icon: Clock3,
        accent: "fuchsia",
      },
    ],
    [overview],
  );

  const accentMap = {
    cyan: "text-cyan-400 bg-cyan-950/60 border-cyan-900/60",
    indigo: "text-indigo-400 bg-indigo-950/60 border-indigo-900/60",
    emerald: "text-emerald-400 bg-emerald-950/60 border-emerald-900/60",
    rose: "text-rose-400 bg-rose-950/60 border-rose-900/60",
    amber: "text-amber-400 bg-amber-950/60 border-amber-900/60",
    violet: "text-violet-400 bg-violet-950/60 border-violet-900/60",
    purple: "text-purple-400 bg-purple-950/60 border-purple-900/60",
    red: "text-red-400 bg-red-950/60 border-red-900/60",
    fuchsia: "text-fuchsia-400 bg-fuchsia-950/60 border-fuchsia-900/60",
  };

  if (loading) {
    return (
      <div className="py-20 flex justify-center">
        <PageSkeleton cards={5} rows={4} />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-300 font-mono">
            Admin Console
          </p>
          <h1 className="text-3xl font-black text-white mt-2">
            Admin overview
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Overview of user accounts, analysis activity, and model health.
          </p>
        </div>
        <div className="rounded-xl border border-cyan-500/40 bg-cyan-950/30 px-4 py-3">
          <p className="text-[10px] uppercase tracking-[0.18em] text-cyan-300 font-mono">
            Signed in as
          </p>
          <p className="text-sm font-semibold text-white">
            {user?.name || "Admin"} • {user?.role || "admin"}
          </p>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadAdminData} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        {statCards.map(({ label, value, icon: Icon, accent }) => (
          <div
            key={label}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-mono">
                {label}
              </p>
              <div className={`rounded-xl border p-2 ${accentMap[accent]}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>
            <p className="mt-4 text-3xl font-black text-white font-['Outfit']">
              {value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Analysis volume
              </p>
              <h2 className="text-xl font-bold text-white mt-1">
                Daily throughput
              </h2>
            </div>
            <BarChart3 className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview.charts.analysisVolume}>
                <defs>
                  <linearGradient id="analysisFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  stroke="#64748b"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke="#64748b" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e2e8f0",
                    color: "#0f172a",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#22d3ee"
                  fill="url(#analysisFill)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Prediction distribution
              </p>
              <h2 className="text-xl font-bold text-white mt-1">Outcome mix</h2>
            </div>
            <Layers3 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overview.charts.predictionDistribution}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  stroke="#64748b"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke="#64748b" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e2e8f0",
                    color: "#0f172a",
                  }}
                />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {overview.charts.predictionDistribution.map(
                    (entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={chartColors[index % chartColors.length]}
                      />
                    ),
                  )}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Media type distribution
              </p>
              <h2 className="text-xl font-bold text-white mt-1">
                Inputs by modality
              </h2>
            </div>
            <ImageIcon className="w-5 h-5 text-violet-400" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={overview.charts.mediaTypeDistribution}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={52}
                  outerRadius={82}
                  paddingAngle={4}
                >
                  {overview.charts.mediaTypeDistribution.map((entry, index) => (
                    <Cell
                      key={entry.name}
                      fill={chartColors[index % chartColors.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e2e8f0",
                    color: "#0f172a",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Processing time
              </p>
              <h2 className="text-xl font-bold text-white mt-1">
                Average latency
              </h2>
            </div>
            <Cpu className="w-5 h-5 text-fuchsia-400" />
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={overview.charts.processingTime}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  stroke="#64748b"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis stroke="#64748b" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e2e8f0",
                    color: "#0f172a",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="avgMs"
                  stroke="#f472b6"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 xl:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Users
              </p>
              <h2 className="text-xl font-bold text-white mt-1">
                Registered accounts
              </h2>
            </div>
            <Users className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="space-y-3">
            {overview.users.length === 0 ? (
              <p className="text-sm text-slate-400">No users found.</p>
            ) : (
              overview.users.slice(0, 6).map((userItem) => (
                <div
                  key={userItem.id}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/80 p-3"
                >
                  <div>
                    <p className="font-semibold text-white">{userItem.name}</p>
                    <p className="text-xs text-slate-400">{userItem.email}</p>
                  </div>
                  <span className="text-[10px] uppercase tracking-[0.15em] text-cyan-300 font-mono">
                    {userItem.role}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 xl:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
                Analyses
              </p>
              <h2 className="text-xl font-bold text-white mt-1">
                Latest records
              </h2>
            </div>
            <Activity className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-800">
            <table className="min-w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] tracking-[0.18em] font-mono">
                <tr>
                  <th className="px-3 py-2">File</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Prediction</th>
                  <th className="px-3 py-2">Model</th>
                  <th className="px-3 py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {overview.recentAnalyses.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-3 py-4 text-slate-400 text-center"
                    >
                      No analyses yet.
                    </td>
                  </tr>
                ) : (
                  overview.recentAnalyses.slice(0, 6).map((item) => (
                    <tr
                      key={item._id || item.id}
                      className="border-t border-slate-800 hover:bg-slate-900/60"
                    >
                      <td className="px-3 py-3 font-medium text-white">
                        {item.filename || "Unknown file"}
                      </td>
                      <td className="px-3 py-3 uppercase">
                        {item.mediaType || "image"}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.12em] font-mono ${
                            item.prediction === "REAL"
                              ? "bg-emerald-500/15 text-emerald-300"
                              : item.prediction === "FAKE"
                                ? "bg-rose-500/15 text-rose-300"
                                : "bg-amber-500/15 text-amber-300"
                          }`}
                        >
                          {item.prediction || "UNCERTAIN"}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-slate-300">
                        {item.modelVersion || "AIDE"}
                      </td>
                      <td className="px-3 py-3 text-slate-300">
                        {Math.round(Number(item.processingTime || 0))} ms
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400 font-mono">
              Model information
            </p>
            <h2 className="text-xl font-bold text-white mt-1">
              Version performance
            </h2>
          </div>
          <Cpu className="w-5 h-5 text-indigo-400" />
        </div>

        <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-200">
          Read-only model access. Weight updates are not exposed through the web
          UI and cannot be modified here.
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {models.length === 0 ? (
            <p className="text-slate-400 text-sm">
              No model metadata available.
            </p>
          ) : (
            models.map((model) => (
              <div
                key={model.modelVersion}
                className="rounded-xl border border-slate-800 bg-slate-900/80 p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="font-bold text-white">{model.modelVersion}</p>
                  <span className="rounded-full bg-cyan-500/10 text-cyan-300 text-[10px] uppercase tracking-[0.15em] font-mono px-2 py-1">
                    {model.analysisCount} runs
                  </span>
                </div>
                <ul className="space-y-2 text-sm text-slate-300">
                  <li className="flex justify-between">
                    <span>Avg confidence</span>
                    <strong className="text-white">
                      {Number(model.averageConfidence || 0).toFixed(3)}
                    </strong>
                  </li>
                  <li className="flex justify-between">
                    <span>Avg latency</span>
                    <strong className="text-white">
                      {model.avgProcessingTimeMs || 0} ms
                    </strong>
                  </li>
                  <li className="flex justify-between">
                    <span>Real rate</span>
                    <strong className="text-white">
                      {Number(model.realRate || 0).toFixed(3)}
                    </strong>
                  </li>
                  <li className="flex justify-between">
                    <span>Fake rate</span>
                    <strong className="text-white">
                      {Number(model.fakeRate || 0).toFixed(3)}
                    </strong>
                  </li>
                  <li className="flex justify-between">
                    <span>Uncertain rate</span>
                    <strong className="text-white">
                      {Number(model.uncertainRate || 0).toFixed(3)}
                    </strong>
                  </li>
                </ul>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
