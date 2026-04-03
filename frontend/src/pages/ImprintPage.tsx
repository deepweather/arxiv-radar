import { Link } from "react-router-dom";

const env = import.meta.env;

const company = env.VITE_IMPRINT_COMPANY;
const representative = env.VITE_IMPRINT_REPRESENTATIVE;
const address = env.VITE_IMPRINT_ADDRESS;
const email = env.VITE_IMPRINT_EMAIL;
const phone = env.VITE_IMPRINT_PHONE;
const register = env.VITE_IMPRINT_REGISTER;
const vatId = env.VITE_IMPRINT_VAT_ID;

const hasImprint = company || representative || address || email;

export default function ImprintPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-12">
      <div className="max-w-xl mx-auto space-y-8">
        <div>
          <Link
            to="/"
            className="text-2xl font-bold text-brand-700 dark:text-brand-400 hover:text-brand-600 dark:hover:text-brand-300"
          >
            arxiv radar
          </Link>
          <h1 className="mt-4 text-xl font-semibold text-gray-900 dark:text-gray-100">
            Legal Notice (Impressum)
          </h1>
        </div>

        {hasImprint ? (
          <div className="space-y-6 text-sm text-gray-700 dark:text-gray-300">
            {company && (
              <Section title="Company">
                <p className="font-medium">{company}</p>
                {representative && <p>Represented by: {representative}</p>}
              </Section>
            )}

            {address && (
              <Section title="Address">
                {address.split("\\n").map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </Section>
            )}

            {(email || phone) && (
              <Section title="Contact">
                {email && (
                  <p>
                    Email:{" "}
                    <a
                      href={`mailto:${email}`}
                      className="text-brand-600 dark:text-brand-400 hover:underline"
                    >
                      {email}
                    </a>
                  </p>
                )}
                {phone && <p>Phone: {phone}</p>}
              </Section>
            )}

            {register && (
              <Section title="Register Entry">
                <p>{register}</p>
              </Section>
            )}

            {vatId && (
              <Section title="VAT ID">
                <p>{vatId}</p>
              </Section>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Imprint information has not been configured. Set the{" "}
            <code className="text-xs bg-gray-200 dark:bg-gray-800 px-1.5 py-0.5 rounded">
              VITE_IMPRINT_*
            </code>{" "}
            environment variables to populate this page.
          </p>
        )}

        <Link
          to="/"
          className="inline-block text-sm text-brand-600 dark:text-brand-400 hover:underline"
        >
          &larr; Back to home
        </Link>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-1">
        {title}
      </h2>
      {children}
    </div>
  );
}
