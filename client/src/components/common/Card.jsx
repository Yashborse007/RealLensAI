import React from 'react';

export default function Card({
  children,
  title = null,
  subtitle = null,
  icon: Icon = null,
  action = null,
  hoverable = true,
  className = '',
  bodyClassName = '',
}) {
  return (
    <div
      className={`glass-card rounded-xl ${
        hoverable ? 'glass-card-hover' : ''
      } overflow-hidden ${className}`}
    >
      {(title || subtitle || Icon || action) && (
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            {Icon && (
              <div className="p-2.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-100">
                <Icon className="w-5 h-5" />
              </div>
            )}
            <div>
              {title && (
                <h3 className="font-semibold text-base text-slate-900 tracking-tight">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
              )}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>{children}</div>
    </div>
  );
}
