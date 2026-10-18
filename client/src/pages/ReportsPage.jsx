import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Download,
  Eye,
  Search,
  FileCheck2,
  ShieldCheck,
} from "lucide-react";

import Card from "../components/common/Card";
import Button from "../components/common/Button";
import StatusBadge from "../components/common/StatusBadge";
import PageSkeleton from "../components/common/PageSkeleton";
import Modal from "../components/common/Modal";
import ErrorMessage from "../components/common/ErrorMessage";
import SampleDataNotice from "../components/common/SampleDataNotice";
import { useToast } from "../context/ToastContext";
import { getReportsList, saveReportToDatabase } from "../services/api";
import { generateAnalysisReportPdf } from "../utils/reportPdf";

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [previewReport, setPreviewReport] = useState(null);
  const [error, setError] = useState(null);
  const [isSampleData, setIsSampleData] = useState(false);
  const { notify } = useToast();

  useEffect(() => {
    const fetchReports = async () => {
      setLoading(true);
      try {
        const data = await getReportsList();
        setReports(data);
        setIsSampleData(Boolean(data?.isSampleData));
      } catch (err) {
        setError(err?.message || "Unable to load reports.");
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, []);

  const filteredReports = reports.filter(
    (rep) =>
      String(rep.title || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(rep.fileName || "").toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const handleDownload = (report) => {
    try {
      const result = generateAnalysisReportPdf(report);
      if (result.fileName) {
        saveReportToDatabase(report.id || report.analysisId || report.mediaId, result.fileName, result.base64);
      }
      notify(`Downloaded: ${result.fileName}`, "success");
    } catch (err) {
      notify(err?.message || "The report could not be generated.", "error");
    }
  };

  if (loading) {
    return (
      <PageSkeleton cards={2} rows={4} />
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white font-['Outfit'] tracking-tight">
            Reports
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Preview or download a PDF summary for a completed analysis.
          </p>
        </div>
        {error && <ErrorMessage title="Reports unavailable" message={error} />}
        {isSampleData && <SampleDataNotice />}

        <Link to="/analyze">
          <Button variant="primary" size="md" icon={FileText}>
            New analysis
          </Button>
        </Link>
      </div>

      {/* Search Bar */}
      <Card hoverable={false} className="border-slate-800">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
          <input
            type="text"
            value={searchTerm}
            aria-label="Search reports"
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search report titles or filenames..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        </div>
      </Card>

      {/* Reports Grid */}
      {filteredReports.length === 0 ? (
        <Card hoverable={false} className="py-14 text-center">
          <FileText className="mx-auto mb-3 h-8 w-8 text-slate-400" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-slate-900">
            {reports.length ? "No matching reports" : "No reports yet"}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
            {reports.length
              ? "Try a different search term."
              : "Reports become available after a media analysis has completed."}
          </p>
          {!reports.length && (
            <Link to="/analyze" className="mt-4 inline-flex">
              <Button variant="primary">Analyze media</Button>
            </Link>
          )}
        </Card>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredReports.map((report) => (
          <div
            key={report.id}
            className="glass-card glass-card-hover rounded-2xl p-6 space-y-4 border border-slate-800/80 flex flex-col justify-between"
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="p-3 rounded-xl bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
                  <FileCheck2 className="w-6 h-6" />
                </div>
                <StatusBadge status={report.result} size="sm" />
              </div>

              <div>
                <h3 className="font-bold text-base text-white font-['Outfit']">
                  {report.title}
                </h3>
                <p className="font-mono text-xs text-cyan-400 mt-1">
                  {report.fileName}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-2 p-3 rounded-xl bg-slate-950/60 font-mono text-[11px] text-slate-400 border border-slate-800/60">
                <div>
                  <span className="text-slate-500 block">Modality:</span>
                  <span className="capitalize text-slate-200">{report.mediaType || "Image"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Confidence:</span>
                  <span className="text-cyan-300 font-bold">
                    {Math.round(Number(report.confidenceScore ?? report.confidence ?? 0.85) * 100)}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Generated:</span>
                  <span className="truncate block">
                    {new Date(report.generatedAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                icon={Eye}
                onClick={() => setPreviewReport(report)}
              >
                Preview
              </Button>

              <Button
                variant="outline"
                size="sm"
                icon={Download}
                onClick={() => handleDownload(report)}
              >
                Download PDF
              </Button>
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Preview Modal */}
      {previewReport && (
        <Modal
          isOpen={!!previewReport}
          onClose={() => setPreviewReport(null)}
          title={`Report Preview: ${previewReport.fileName}`}
          footer={
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPreviewReport(null)}
              >
                Close Preview
              </Button>
              <Button
                variant="primary"
                size="sm"
                icon={Download}
                onClick={() => {
                  handleDownload(previewReport);
                  setPreviewReport(null);
                }}
              >
                Download PDF
              </Button>
            </>
          }
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-center">
              <ShieldCheck className="w-8 h-8 text-cyan-400 mx-auto" />
              <h4 className="font-bold text-sm text-white font-['Outfit']">
                {previewReport.title}
              </h4>
              <p className="text-[11px] text-slate-400">
                Author: {previewReport.author}
              </p>
            </div>

            <div className="space-y-2 p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-300">
              <p>
                <strong>Report ID:</strong> {previewReport.id}
              </p>
              <p>
                <strong>Associated Analysis:</strong> {previewReport.analysisId}
              </p>
              <p>
                <strong>Result:</strong> {String(previewReport.result || "uncertain").toUpperCase()}
              </p>
              <p>
                <strong>Confidence:</strong>{" "}
                {Math.round(previewReport.confidenceScore * 100)}%
              </p>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
