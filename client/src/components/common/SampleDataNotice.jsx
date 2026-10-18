import React from "react";
import { Info } from "lucide-react";

export default function SampleDataNotice() {
  return (
    <div
      role="status"
      className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>
        Sample data is shown because live service data could not be loaded. It
        does not represent your account or a real analysis.
      </p>
    </div>
  );
}
