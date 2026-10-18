import React from "react";

export default function PageSkeleton({ rows = 4, cards = 3 }) {
  return (
    <div
      className="space-y-6"
      role="status"
      aria-label="Loading page content"
      aria-busy="true"
    >
      <span className="sr-only">Loading page content</span>
      <div className="space-y-3 border-b border-slate-200 pb-5">
        <div className="skeleton h-7 w-2/5 max-w-sm rounded-md" />
        <div className="skeleton h-4 w-3/5 max-w-xl rounded-md" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: cards }, (_, index) => (
          <div
            key={index}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <div className="skeleton mb-5 h-4 w-2/3 rounded" />
            <div className="skeleton mb-3 h-8 w-1/2 rounded" />
            <div className="skeleton h-3 w-4/5 rounded" />
          </div>
        ))}
      </div>
      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className="skeleton h-12 w-full rounded-lg"
          />
        ))}
      </div>
    </div>
  );
}
