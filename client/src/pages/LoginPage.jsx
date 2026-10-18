import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, Mail, Lock, LogIn } from "lucide-react";
import Button from "../components/common/Button";
import Card from "../components/common/Card";
import ErrorMessage from "../components/common/ErrorMessage";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, authError } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const fromPath = location.state?.from?.pathname || "/dashboard";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);

    // Basic frontend field validation
    if (!email || !password) {
      setErrorMsg("Please enter both email address and password.");
      return;
    }

    setIsLoading(true);
    let result;
    try {
      result = await login(email, password);
    } finally {
      setIsLoading(false);
    }

    if (result.success) {
      navigate(fromPath, { replace: true });
    } else {
      setErrorMsg(result.error);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShieldCheck className="w-7 h-7 text-slate-950 stroke-[2.5]" />
          </div>
          <h1 className="text-2xl font-extrabold text-white font-['Outfit'] tracking-tight">
            Sign In to RealLens AI
          </h1>
          <p className="text-xs text-slate-400">
            Enter investigator credentials to access protected forensic tools
          </p>
        </div>

        {(errorMsg || authError) && (
          <ErrorMessage
            title="Authentication Error"
            message={errorMsg || authError}
            dismissable
            onDismiss={() => setErrorMsg(null)}
          />
        )}

        <Card hoverable={false} className="border-slate-800">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="text-xs font-semibold text-slate-300 flex items-center gap-1.5"
              >
                <Mail className="w-3.5 h-3.5 text-cyan-400" />
                Investigator Email
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="email"
                autoCapitalize="none"
                spellCheck="false"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@forensics.org"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label
                  htmlFor="login-password"
                  className="text-xs font-semibold text-slate-300 flex items-center gap-1.5"
                >
                  <Lock className="w-3.5 h-3.5 text-cyan-400" />
                  Password
                </label>
              </div>
              <input
                id="login-password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition-colors"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              icon={LogIn}
              className="w-full font-bold py-3 mt-2"
            >
              Sign In to Portal
            </Button>
          </form>
        </Card>

        <div className="text-center text-xs text-slate-400 space-y-2">
          <p>
            Don't have an investigator account?{" "}
            <Link
              to="/register"
              className="text-cyan-400 font-semibold hover:underline"
            >
              Register Organization
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
