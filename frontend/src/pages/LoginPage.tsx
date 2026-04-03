import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useLogin } from "@/hooks/useAuth";
import { getHttpStatus } from "@/api/errors";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [company, setCompany] = useState("");
  const loadedAt = useRef(Date.now() / 1000);
  const login = useLogin();

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
            <p className="text-sm text-red-600">
              {getHttpStatus(login.error) === 429
                ? "Too many attempts. Please wait a moment."
                : "Invalid credentials. Please try again."}
            </p>
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
