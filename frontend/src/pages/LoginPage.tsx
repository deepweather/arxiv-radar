import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useLogin, useResendVerification } from "@/hooks/useAuth";
import { getHttpStatus } from "@/api/errors";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [company, setCompany] = useState("");
  const loadedAt = useRef(Date.now() / 1000);
  const login = useLogin();
  const resend = useResendVerification();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate({
      email,
      password,
      company,
      tz_offset: loadedAt.current,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <Link to="/" className="text-2xl font-bold text-brand-700 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300">arxiv radar</Link>
          <p className="mt-2 text-gray-500 dark:text-gray-400">Sign in to your account</p>
        </div>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-brand-500 outline-none"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-brand-500 outline-none"
          />
          <div style={{ opacity: 0, height: 0, overflow: "hidden", position: "absolute" }}>
            <input
              type="text"
              name="company"
              tabIndex={-1}
              autoComplete="new-password"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-xs text-brand-600 dark:text-brand-400 hover:underline">
              Forgot password?
            </Link>
          </div>
          {login.isError && (
            <div className="text-sm">
              {getHttpStatus(login.error) === 429 ? (
                <p className="text-red-600">Too many attempts. Please wait a moment.</p>
              ) : getHttpStatus(login.error) === 403 ? (
                <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800">
                  <p className="text-amber-800 dark:text-amber-200">
                    Please verify your email before signing in.
                  </p>
                  <button
                    type="button"
                    onClick={() => resend.mutate(email)}
                    disabled={resend.isPending || resend.isSuccess}
                    className="mt-2 text-brand-600 dark:text-brand-400 hover:underline disabled:opacity-50"
                  >
                    {resend.isPending ? "Sending..." : resend.isSuccess ? "Verification email sent!" : "Resend verification email"}
                  </button>
                </div>
              ) : (
                <p className="text-red-600">Invalid credentials. Please try again.</p>
              )}
            </div>
          )}
          <button
            type="submit"
            disabled={login.isPending}
            className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {login.isPending ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          No account?{" "}
          <Link to="/register" className="text-brand-600 dark:text-brand-400 hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
