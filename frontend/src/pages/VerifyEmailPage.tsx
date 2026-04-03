import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/api/client";
import { AxiosError } from "axios";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Invalid verification link. No token provided.");
      return;
    }

    api
      .post("/auth/verify-email", { token })
      .then(() => {
        setStatus("success");
        setMessage("Your email has been verified!");
      })
      .catch((err) => {
        setStatus("error");
        if (err instanceof AxiosError) {
          setMessage(err.response?.data?.detail || "Verification failed.");
        } else {
          setMessage("Something went wrong.");
        }
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <div className="w-full max-w-sm text-center space-y-6">
        <Link to="/" className="text-2xl font-bold text-brand-700 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300">
          arxiv radar
        </Link>

        {status === "loading" && (
          <p className="text-gray-500 dark:text-gray-400">Verifying your email...</p>
        )}

        {status === "success" && (
          <div className="space-y-4">
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <p className="text-green-800 dark:text-green-300 text-sm">{message}</p>
            </div>
            <Link
              to="/"
              className="inline-block py-2.5 px-6 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors"
            >
              Go to dashboard
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-4">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-800 dark:text-red-300 text-sm">{message}</p>
            </div>
            <Link to="/login" className="text-sm text-brand-600 dark:text-brand-400 hover:underline">
              Go to sign in
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
