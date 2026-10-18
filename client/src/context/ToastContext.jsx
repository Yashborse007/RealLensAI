import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

const ToastContext = createContext(null);

const toastTypes = {
  success: {
    Icon: CheckCircle2,
    className: "border-emerald-200 bg-white text-emerald-900",
  },
  error: {
    Icon: AlertCircle,
    className: "border-rose-200 bg-white text-rose-900",
  },
  info: {
    Icon: Info,
    className: "border-blue-200 bg-white text-slate-900",
  },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef(new Map());

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
    timers.current.delete(id);
  }, []);

  const notify = useCallback(
    (message, type = "info") => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const toast = { id, message: String(message), type };
      setToasts((current) => [...current.slice(-3), toast]);
      timers.current.set(id, setTimeout(() => dismissToast(id), 5000));
      return id;
    },
    [dismissToast],
  );

  useEffect(
    () => () => {
      timers.current.forEach((timer) => clearTimeout(timer));
      timers.current.clear();
    },
    [],
  );

  return (
    <ToastContext.Provider value={{ notify, dismissToast }}>
      {children}
      <div
        className="fixed right-4 top-20 z-[70] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
        aria-label="Notifications"
        aria-live="polite"
        aria-relevant="additions removals"
      >
        {toasts.map((toast) => {
          const config = toastTypes[toast.type] || toastTypes.info;
          const Icon = config.Icon;
          return (
            <div
              key={toast.id}
              role={toast.type === "error" ? "alert" : "status"}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg ${config.className}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p className="flex-1 text-sm leading-5">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider.");
  return context;
}
