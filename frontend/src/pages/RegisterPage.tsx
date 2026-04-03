import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { useRegister } from "@/hooks/useAuth";
import { getHttpStatus } from "@/api/errors";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [company, setCompany] = useState("");
  const loadedAt = useRef(Date.now() / 1000);
  const register = useRegister();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    register.mutate({
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
          <p className="mt-2 text-gray-500 dark:text-gray-400">Create your account</p>
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
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
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
          {register.isError && (
            <p className="text-sm text-red-600">
              {getHttpStatus(register.error) === 429
                ? "Too many attempts. Please wait before trying again."
                : "Registration failed. Email may already be registered."}
            </p>
          )}
          <button
            type="submit"
            disabled={register.isPending}
            className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {register.isPending ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-600 dark:text-brand-400 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
