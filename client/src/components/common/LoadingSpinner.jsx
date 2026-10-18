import React from 'react';
import { LoaderCircle } from 'lucide-react';

export default function LoadingSpinner({
  label = 'Working on your request…',
  sublabel = 'This may take a moment.',
  size = 'md', // 'sm' | 'md' | 'lg'
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4 text-center">
      <div className="flex items-center justify-center" aria-hidden="true">
        <LoaderCircle className="h-8 w-8 animate-spin text-blue-700" />
      </div>

      {label && (
        <div className="space-y-1">
          <p className="text-sm font-semibold text-slate-800 tracking-wide">
            {label}
          </p>
          {sublabel && (
            <p className="text-xs text-slate-400 max-w-xs">{sublabel}</p>
          )}
        </div>
      )}
    </div>
  );
}
