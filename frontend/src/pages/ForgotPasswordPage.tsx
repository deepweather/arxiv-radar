import { useState } from "react";
import { Link } from "react-router-dom";
import api from "@/api/client";
import { getHttpStatus } from "@/api/errors";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (err) {
      if (getHttpStatus(err) === 429) {
        setError("Too many attempts. Please wait a moment.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <Link to="/" className="text-2xl font-bold text-brand-700 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300">
            arxiv radar
          </Link>
          <p className="mt-2 text-gray-500 dark:text-gray-400">Reset your password</p>
        </div>

        {submitted ? (
          <div className="text-center space-y-4">
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <p className="text-green-800 dark:text-green-300 text-sm">
                If an account exists with that email, we've sent a password reset link. Check your inbox.
              </p>
            </div>
            <Link to="/login" className="text-sm text-brand-600 dark:text-brand-400 hover:underline">
              Back to sign in
            </Link>
          </div>
        ) : (
          <>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-brand-500 outline-none"
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium transition-colors"
              >
                {loading ? "Sending..." : "Send reset link"}
              </button>
            </form>
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              Remember your password?{" "}
              <Link to="/login" className="text-brand-600 dark:text-brand-400 hover:underline">
                Sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
