import React, { useId } from "react";

export default function Tooltip({ text, children }) {
  const tooltipId = useId();
  return (
    <span
      className="tooltip-group relative inline-flex"
      tabIndex={0}
      aria-describedby={tooltipId}
    >
      {children}
      <span id={tooltipId} role="tooltip" className="tooltip-content">
        {text}
      </span>
    </span>
  );
}
