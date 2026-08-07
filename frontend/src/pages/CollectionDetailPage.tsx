import { useState, useCallback, useRef, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Globe, Lock, Share2, Check, Eye, FileText, User as UserIcon, Download, Loader2 } from "lucide-react";
import { useCollection } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";
import PaperList from "@/components/papers/PaperList";

const DOWNLOAD_PAPER_LIMIT = 50; // keep in sync with backend MAX_PAPERS
const DEFAULT_ZIP_FILENAME = "collection.zip";

export default function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useCollection(id!);
  const user = useAuthStore((s) => s.user);
  const [copied, setCopied] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const toggleSelect = useCallback((pid: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  }, []);

  const selectAllVisible = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleDownload = useCallback(async () => {
    if (!id) return;
    abortRef.current?.abort();

    const controller = new AbortController();
    abortRef.current = controller;

    let url = `/api/collections/${id}/download`;
    if (selectedIds.size > 0) {
      url += `?ids=${Array.from(selectedIds).map(encodeURIComponent).join(",")}`;
    }

    setDownloadError("");
    setDownloading(true);

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        credentials: "include",
      });

      if (!response.ok) {
        let message = "Download failed. Please try again.";
        try {
          const errorBody = await response.json();
          if (typeof errorBody.detail === "string") {
            message = errorBody.detail;
          }
        } catch {
          // Keep generic error when the response is not JSON.
        }
        setDownloadError(message);
        return;
      }

      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") ?? "";
      const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
      const quotedMatch = disposition.match(/filename="([^"]+)"/i);
      const filename = utf8Match
        ? decodeURIComponent(utf8Match[1])
        : quotedMatch?.[1] ?? DEFAULT_ZIP_FILENAME;

      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setDownloadError("Download failed. Please try again.");
    } finally {
      if (abortRef.current === controller) {
        setDownloading(false);
        abortRef.current = null;
      }
    }
  }, [id, selectedIds]);

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-gray-100 dark:bg-gray-800 rounded-xl" />;
  }

  if (!data) {
    return <div className="text-gray-500">Collection not found.</div>;
  }

  const isOwner = data.is_owner ?? false;
  const showDownloadUI = data.is_public === true && !isOwner;
  const effectiveCount = selectedIds.size > 0 ? selectedIds.size : data.papers?.length ?? 0;
  const overLimit = effectiveCount > DOWNLOAD_PAPER_LIMIT;
  const noPapers = effectiveCount === 0;
  const downloadDisabled = downloading || overLimit || noPapers;
  const backLink = isOwner ? "/collections" : "/collections/explore";
  const backLabel = isOwner ? "Back to collections" : "Back to explore";

  const downloadLabel =
    selectedIds.size === 0
      ? `Download all PDFs (${data.papers?.length ?? 0})`
      : selectedIds.size === 1
      ? "Download 1 PDF"
      : `Download ${selectedIds.size} PDFs`;

  const downloadAction = (
    <div className="flex flex-col">
      <button
        onClick={handleDownload}
        disabled={downloadDisabled}
        aria-label={downloadLabel}
        aria-busy={downloading}
        aria-describedby={overLimit ? "download-limit-msg" : undefined}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
        {downloadLabel}
      </button>
      {overLimit && (
        <p id="download-limit-msg" role="status" aria-live="polite" className="mt-1 text-xs text-red-600 dark:text-red-400">
          Select up to 50 papers to download.
        </p>
      )}
      {downloadError && (
        <p role="alert" aria-live="assertive" className="mt-1 text-xs text-red-600 dark:text-red-400">
          {downloadError}
        </p>
      )}
    </div>
  );

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
        selectable={showDownloadUI}
        selectedIds={showDownloadUI ? selectedIds : undefined}
        onToggleSelect={showDownloadUI ? toggleSelect : undefined}
        onSelectAllVisible={showDownloadUI ? selectAllVisible : undefined}
        onClearSelection={showDownloadUI ? clearSelection : undefined}
        downloadAction={showDownloadUI ? downloadAction : undefined}
      />
    </div>
  );
}
