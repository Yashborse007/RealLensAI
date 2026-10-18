import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Activity, 
  CheckCircle2, 
  AlertOctagon, 
  FileText, 
  TrendingUp, 
  UploadCloud, 
  BarChart2, 
  PieChart as PieIcon,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  PieChart, 
  Pie, 
  Cell,
  BarChart,
  Bar,
  Legend
} from 'recharts';

import Card from '../components/common/Card';
import Button from '../components/common/Button';
import AnalysisCard from '../components/analysis/AnalysisCard';
import PageSkeleton from '../components/common/PageSkeleton';
import ErrorMessage from '../components/common/ErrorMessage';
import SampleDataNotice from '../components/common/SampleDataNotice';
import { getDashboardStats, getDistributionData, getRecentAnalyses } from '../services/api';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [distribution, setDistribution] = useState([]);
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSampleData, setIsSampleData] = useState(false);
  const authenticitySummary = [
    { name: "Likely authentic", value: stats?.realMediaCount ?? 0, color: "#15803d" },
    { name: "Potentially manipulated", value: stats?.potentialDeepfakesCount ?? 0, color: "#b91c1c" },
    { name: "Uncertain", value: stats?.uncertainMediaCount ?? 0, color: "#a16207" },
  ];
  const authenticityTotal = authenticitySummary.reduce((sum, item) => sum + item.value, 0);
  const hasAuthenticityData = authenticityTotal > 0;

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sData, dData, rData] = await Promise.all([
        getDashboardStats(),
        getDistributionData(),
        getRecentAnalyses(),
      ]);
      setStats(sData);
      setDistribution(dData);
      setRecentAnalyses(rData);
      setIsSampleData(
        Boolean(sData?.isSampleData || dData?.isSampleData || rData?.isSampleData),
      );
    } catch (err) {
      setError(err?.message || 'Unable to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="py-20 flex justify-center">
        <PageSkeleton cards={4} rows={3} />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-['Outfit'] tracking-tight">
            Your analysis overview
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            A clear summary of your media checks and recent results.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadDashboardData}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
            title="Refresh dashboard"
            aria-label="Refresh dashboard"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          
          <Link to="/analyze">
            <Button variant="primary" size="md" icon={UploadCloud}>
              New analysis
            </Button>
          </Link>
        </div>
      </div>

      {error && <ErrorMessage message={error} onRetry={loadDashboardData} />}
      {isSampleData && <SampleDataNotice />}

      {/* 4 Required Metric Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Stat 1: Total Analyses */}
        <div className="glass-card glass-card-hover rounded-2xl p-5 space-y-3 border border-cyan-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Total analyses
            </span>
            <div className="p-2.5 rounded-xl bg-cyan-950/80 text-cyan-400 border border-cyan-800/50">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-black text-white font-['Outfit']">
              {stats?.totalAnalyses ?? 0}
            </span>
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
              <TrendingUp className="w-3.5 h-3.5" />
              {stats?.weeklyGrowthRate ?? '—'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Processed across image, video & audio</p>
        </div>

        {/* Stat 2: Real Media */}
        <div className="glass-card glass-card-hover rounded-2xl p-5 space-y-3 border border-emerald-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Likely authentic
            </span>
            <div className="p-2.5 rounded-xl bg-emerald-950/80 text-emerald-400 border border-emerald-800/50">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-black text-white font-['Outfit']">
              {stats?.realMediaCount ?? 0}
            </span>
            <span className="text-xs font-mono text-emerald-400">
              {stats?.totalAnalyses ? Math.round(((stats.realMediaCount ?? 0) / stats.totalAnalyses) * 100) : 0}% of total
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Model-predicted authentic</p>
        </div>

        {/* Stat 3: Potential Deepfakes */}
        <div className="glass-card glass-card-hover rounded-2xl p-5 space-y-3 border border-rose-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Potentially manipulated
            </span>
            <div className="p-2.5 rounded-xl bg-rose-950/80 text-rose-400 border border-rose-800/50">
              <AlertOctagon className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-black text-white font-['Outfit']">
              {stats?.potentialDeepfakesCount ?? 0}
            </span>
            <span className="text-xs font-mono text-rose-400">
              {stats?.totalAnalyses ? Math.round(((stats.potentialDeepfakesCount ?? 0) / stats.totalAnalyses) * 100) : 0}% of total
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Model-predicted; review the evidence</p>
        </div>

        {/* Stat 4: Reports Generated */}
        <div className="glass-card glass-card-hover rounded-2xl p-5 space-y-3 border border-indigo-500/20">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Reports generated
            </span>
            <div className="p-2.5 rounded-xl bg-indigo-950/80 text-indigo-400 border border-indigo-800/50">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-black text-white font-['Outfit']">
              {stats?.reportsGenerated ?? 0}
            </span>
            <span className="text-xs font-mono text-indigo-400">PDF Audit Logs</span>
          </div>
          <p className="text-[11px] text-slate-500">PDF analysis summaries</p>
        </div>

      </div>

      {/* Charts Section: 6. Analysis Distribution Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Distribution Area/Bar Chart */}
        <Card
          title="Analysis Distribution & Modality Trends"
          subtitle="Recent checks by media type"
          icon={BarChart2}
          className="lg:col-span-2 border-slate-800"
        >
          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={distribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorImages" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#00f0ff" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorVideo" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDeepfakes" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', color: '#0f172a', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="images" name="Images" stroke="#00f0ff" fillOpacity={1} fill="url(#colorImages)" strokeWidth={2} />
                <Area type="monotone" dataKey="video" name="Video Frames" stroke="#6366f1" fillOpacity={1} fill="url(#colorVideo)" strokeWidth={2} />
                <Area type="monotone" dataKey="deepfakes" name="Deepfakes Flagged" stroke="#f43f5e" fillOpacity={1} fill="url(#colorDeepfakes)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Authenticity Summary Pie Chart */}
        <Card
          title="Authenticity Share"
          subtitle="Share of model outcomes"
          icon={PieIcon}
          className="border-slate-800"
        >
          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={authenticitySummary}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {authenticitySummary.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', color: '#0f172a', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {hasAuthenticityData ? (
            <div className="flex flex-wrap justify-around gap-3 pt-2 text-xs font-semibold">
              {authenticitySummary.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-slate-600">
                    {item.name} ({Math.round((item.value / authenticityTotal) * 100)}%)
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500">
              Results will appear here after analyses are completed.
            </p>
          )}
        </Card>

      </div>

      {/* 5. Recent Analyses Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <h2 className="text-xl font-bold text-white font-['Outfit']">
              Recent analyses
            </h2>
          </div>

          <Link
            to="/history"
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <span>View all analyses</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recentAnalyses.slice(0, 6).map((item) => (
            <AnalysisCard key={item.id} analysis={item} />
          ))}
          {recentAnalyses.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center md:col-span-2 lg:col-span-3">
              <p className="font-medium text-slate-800">No analyses yet</p>
              <p className="mt-1 text-sm text-slate-500">
                Upload an image, video, or audio file to get started.
              </p>
              <Link to="/analyze" className="mt-4 inline-flex">
                <Button variant="primary">Analyze media</Button>
              </Link>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
