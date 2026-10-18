import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  History,
  Search,
  ArrowRight,
  Video as VideoIcon,
  Mic as AudioIcon,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import Card from "../components/common/Card";
import Button from "../components/common/Button";
import StatusBadge from "../components/common/StatusBadge";
import PageSkeleton from "../components/common/PageSkeleton";
import ErrorMessage from "../components/common/ErrorMessage";
import SampleDataNotice from "../components/common/SampleDataNotice";
import { getUserAnalyses } from "../services/api";

const normalizeResult = (value) => {
  const raw = String(value || "").toLowerCase();
  if (raw === "real" || raw === "authentic") return "authentic";
  if (raw === "fake" || raw === "manipulated" || raw === "deepfake")
    return "manipulated";
  if (raw === "uncertain" || raw === "suspicious" || raw === "anomalous")
    return "suspicious";
  return "suspicious";
};

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedMediaType, setSelectedMediaType] = useState("all");
  const [selectedResult, setSelectedResult] = useState("all");
  const [sortDirection, setSortDirection] = useState("newest");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(8);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState(null);
  const [isSampleData, setIsSampleData] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getUserAnalyses({
          page: currentPage,
          limit: pageSize,
          mediaType: selectedMediaType,
          result: selectedResult,
          sort: sortDirection,
          search: searchTerm,
        });
        setAnalyses(data.data || []);
        setTotalPages(data.totalPages || 1);
        setIsSampleData(Boolean(data.isSampleData || data.data?.isSampleData));
      } catch (err) {
        setError(err?.message || "Unable to load your analysis history.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [
    currentPage,
    pageSize,
    selectedMediaType,
    selectedResult,
    sortDirection,
    searchTerm,
  ]);

  const resetFilters = () => {
    setSearchTerm("");
    setSelectedMediaType("all");
    setSelectedResult("all");
    setSortDirection("newest");
    setCurrentPage(1);
  };

  const formattedAnalyses = analyses.map((item) => ({
    ...item,
    fileName: item.filename || item.fileName || "Unknown file",
    mediaType: String(item.mediaType || "image").toLowerCase(),
    result: normalizeResult(
      item.prediction || item.result || item.status || "UNCERTAIN",
    ),
    uploadedAt: item.createdAt || item.uploadedAt || new Date().toISOString(),
    fileSize: item.fileSize || "—",
  }));

  if (loading) {
    return (
      <div className="py-20 flex justify-center">
        <PageSkeleton cards={2} rows={5} />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-['Outfit'] tracking-tight">
            Analysis history
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Search and review previous media checks.
          </p>
        </div>

        <Link to="/analyze">
          <Button variant="primary" size="md" icon={History}>
            New analysis
          </Button>
        </Link>
      </div>
      {error && <ErrorMessage title="History unavailable" message={error} />}
      {isSampleData && <SampleDataNotice />}

      <Card hoverable={false} className="border-slate-800">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="md:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setCurrentPage(1);
                setSearchTerm(e.target.value);
              }}
              aria-label="Search analysis history"
              placeholder="Search by filename or analysis ID..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <div>
            <select
              value={selectedMediaType}
              onChange={(e) => {
                setCurrentPage(1);
                setSelectedMediaType(e.target.value);
              }}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="all">All Media Types</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="audio">Audio</option>
            </select>
          </div>

          <div>
            <select
              value={selectedResult}
              onChange={(e) => {
                setCurrentPage(1);
                setSelectedResult(e.target.value);
              }}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="all">All</option>
              <option value="real">Authentic</option>
              <option value="fake">Manipulated</option>
              <option value="uncertain">Uncertain</option>
            </select>
          </div>

          <div>
            <select
              value={sortDirection}
              onChange={(e) => {
                setCurrentPage(1);
                setSortDirection(e.target.value);
              }}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition-colors"
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </div>
        </div>
      </Card>

      {formattedAnalyses.length === 0 ? (
        <Card
          hoverable={false}
          className="border-slate-800 py-16 text-center space-y-4"
        >
          <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
            <History className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white font-['Outfit']">
              No matching analyses
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Try changing your search or filters, or reset them to see all analyses.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={resetFilters}>
            Reset Filters
          </Button>
        </Card>
      ) : (
        <>
          <div className="glass-card rounded-2xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 font-mono uppercase text-slate-400">
                    <th className="py-3.5 px-6 font-semibold">
                      Analysis & file
                    </th>
                    <th className="py-3.5 px-6 font-semibold">Modality</th>
                    <th className="py-3.5 px-6 font-semibold">Confidence</th>
                    <th className="py-3.5 px-6 font-semibold">Analysis Date</th>
                    <th className="py-3.5 px-6 font-semibold">
                      Result
                    </th>
                    <th className="py-3.5 px-6 font-semibold text-right">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {formattedAnalyses.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-900/50 transition-colors"
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 rounded-lg bg-slate-900 text-cyan-400 border border-slate-800">
                            {item.mediaType === "image" && (
                              <ImageIcon className="w-4 h-4" />
                            )}
                            {item.mediaType === "video" && (
                              <VideoIcon className="w-4 h-4" />
                            )}
                            {item.mediaType === "audio" && (
                              <AudioIcon className="w-4 h-4" />
                            )}
                          </div>
                          <div>
                            <p className="font-bold text-sm text-white font-['Outfit']">
                              {item.fileName}
                            </p>
                            <span className="font-mono text-[10px] text-slate-500">
                              {item.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-6 capitalize text-slate-300 font-mono">
                        {item.mediaType}
                      </td>

                      <td className="py-4 px-6 font-mono">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                          Number(item.confidence ?? 0) >= 0.8
                            ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/50"
                            : Number(item.confidence ?? 0) >= 0.6
                              ? "bg-cyan-950/80 text-cyan-300 border border-cyan-800/50"
                              : "bg-amber-950/80 text-amber-300 border border-amber-800/50"
                        }`}>
                          {Math.round(Number(item.confidence ?? 0) * 100)}%
                        </span>
                      </td>

                      <td className="py-4 px-6 text-slate-400 font-mono">
                        {new Date(item.uploadedAt).toLocaleString()}
                      </td>

                      <td className="py-4 px-6">
                        <StatusBadge status={item.result} size="sm" />
                      </td>

                      <td className="py-4 px-6 text-right">
                        <Link
                          to={`/analysis/${item.id}`}
                          className="inline-flex items-center space-x-1 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          <span>Open</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2">
            <Button
              variant="ghost"
              size="sm"
              icon={ChevronLeft}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
            >
              Previous
            </Button>

            <p className="text-xs text-slate-400 font-mono">
              Page {currentPage} / {totalPages}
            </p>

            <Button
              variant="ghost"
              size="sm"
              icon={ChevronRight}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
            >
              Next
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
