import React from 'react';
import { AlertTriangle, RefreshCw, XCircle } from 'lucide-react';
import Button from './Button';

export default function ErrorMessage({
  title = 'Something went wrong',
  message = 'We could not complete that request. Try again in a moment.',
  onRetry = null,
  dismissable = false,
  onDismiss = null,
  className = '',
}) {
  return (
    <div role="alert" className={`p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-rose-200 ${className}`}>
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-lg bg-rose-900/60 text-rose-400 mt-0.5 sm:mt-0 border border-rose-700/50">
          <AlertTriangle className="w-5 h-5" aria-hidden="true" />
        </div>
        <div>
          <h4 className="font-semibold text-sm text-rose-100 font-['Outfit']">{title}</h4>
          <p className="text-xs text-rose-300/80 mt-0.5 leading-relaxed">{message}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2 self-end sm:self-center">
        {onRetry && (
          <Button
            size="sm"
            variant="danger"
            onClick={onRetry}
            icon={RefreshCw}
          >
            Try again
          </Button>
        )}
        {dismissable && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="p-1.5 rounded-lg text-rose-400 hover:text-rose-200 hover:bg-rose-900/40 transition-colors"
          >
            <XCircle className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}
