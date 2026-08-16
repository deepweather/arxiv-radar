import { useState } from "react";
import { Link } from "react-router-dom";
import {
  analyticsAvailable,
  getStoredConsent,
  grantConsent,
  denyConsent,
} from "@/analytics";

export default function ConsentBanner() {
  const [visible, setVisible] = useState(
    () => analyticsAvailable() && getStoredConsent() === null,
  );

  if (!visible) return null;

  const accept = () => {
    grantConsent();
    setVisible(false);
  };

  const decline = () => {
    denyConsent();
    setVisible(false);
  };

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-4 shadow-lg mb-16 md:mb-0"
    >
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row sm:items-center gap-3">
        <p className="flex-1 text-sm text-gray-600 dark:text-gray-300">
          We use Google Analytics to understand how the site is used. Analytics
          cookies are only set if you accept.{" "}
          <Link to="/imprint" className="text-brand-600 dark:text-brand-400 hover:underline">
            Learn more
          </Link>
          .
        </p>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={decline}
            className="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Decline
          </button>
          <button
            onClick={accept}
            className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}
