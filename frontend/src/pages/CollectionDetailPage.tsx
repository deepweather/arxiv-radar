import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Globe, Lock, Share2, Check, Eye, FileText, User as UserIcon } from "lucide-react";
import { useCollection } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";
import PaperList from "@/components/papers/PaperList";

export default function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useCollection(id!);
  const user = useAuthStore((s) => s.user);
  const [copied, setCopied] = useState(false);

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-gray-100 dark:bg-gray-800 rounded-xl" />;
  }

  if (!data) {
    return <div className="text-gray-500">Collection not found.</div>;
  }

  const isOwner = data.is_owner ?? false;
  const backLink = isOwner ? "/collections" : "/collections/explore";
  const backLabel = isOwner ? "Back to collections" : "Back to explore";

  const handleShare = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      <Link
        to={backLink}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600"
      >
        <ArrowLeft size={14} />
        {backLabel}
      </Link>

      <div>
        <div className="flex items-center gap-2 flex-wrap">
          {data.is_public ? (
            <Globe size={16} className="text-green-500" />
          ) : (
            <Lock size={16} className="text-gray-400" />
          )}
          <h1 className="text-2xl font-bold">{data.name}</h1>
          {data.is_public && (
            <button
              onClick={handleShare}
              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900 transition-colors"
            >
              {copied ? <Check size={14} /> : <Share2 size={14} />}
              {copied ? "Copied!" : "Share"}
            </button>
          )}
        </div>
        {data.description && (
          <p className="mt-1 text-gray-500 dark:text-gray-400">{data.description}</p>
        )}
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-400 dark:text-gray-500">
          {data.owner_name && (
            <span className="flex items-center gap-1">
              <UserIcon size={14} />
              {data.owner_name}
            </span>
          )}
          <span className="flex items-center gap-1">
            <FileText size={14} />
            {data.papers?.length ?? 0} papers
          </span>
          {data.view_count != null && (
            <span className="flex items-center gap-1">
              <Eye size={14} />
              {data.view_count} views
            </span>
          )}
        </div>
      </div>

      <PaperList
        papers={data.papers ?? []}
        toolbar
      />
    </div>
  );
}
