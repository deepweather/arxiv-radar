import { useParams, Link } from "react-router-dom";
import { ExternalLink, FileText, ArrowLeft, Bookmark, Tag as TagIcon, FolderPlus, BookOpen, Network, GraduationCap } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { usePaper, useSimilarPapers } from "@/hooks/usePapers";
import { useSavePaper, useUnsavePaper, useSavedPapers } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";
import PaperCard from "@/components/papers/PaperCard";
import TagPicker from "@/components/tags/TagPicker";
import CollectionPicker from "@/components/collections/CollectionPicker";
import LaTeXText from "@/components/common/LaTeXText";
import api from "@/api/client";
import { Paper } from "@/types";
import { useState } from "react";

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const { data: paper, isLoading } = usePaper(id!);
  const { data: similar } = useSimilarPapers(id!);
  const { data: authorPapers } = useQuery<{ papers: Paper[] }>({
    queryKey: ["paper", id, "by-authors"],
    queryFn: async () => {
      const { data } = await api.get(`/papers/${id}/by-authors`);
      return data;
    },
    enabled: !!id,
  });
  const save = useSavePaper();
  const unsave = useUnsavePaper();
  const { data: savedData } = useSavedPapers();
  const [showTagPicker, setShowTagPicker] = useState(false);
  const [showCollectionPicker, setShowCollectionPicker] = useState(false);

  const savedIds = new Set<string>(
    (savedData?.papers ?? []).map((p: Paper) => p.id),
  );
  const isSaved = id ? savedIds.has(id) : false;

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        <div className="space-y-2 mt-6">
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded" />
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded" />
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-4/5" />
        </div>
      </div>
    );
  }

  if (!paper) {
    return <div className="text-gray-500">Paper not found.</div>;
  }

  const authorStr = paper.authors.map((a) => a.name).join(", ");
  const timeAgo = paper.published_at
    ? formatDistanceToNow(new Date(paper.published_at), { addSuffix: true })
    : "";

  return (
    <div className="space-y-8">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600 dark:hover:text-brand-400"
      >
        <ArrowLeft size={14} />
        Back
      </Link>

      <div>
        <LaTeXText as="h1" text={paper.title} className="text-2xl font-bold leading-tight" />
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{authorStr}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-gray-400">{timeAgo}</span>
          {paper.categories.map((cat) => (
            <Link
              key={cat}
              to={`/search?categories=${cat}`}
              className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-950 dark:hover:text-brand-400 transition-colors"
            >
              {cat}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <a
          href={`https://arxiv.org/abs/${paper.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <ExternalLink size={14} />
          View on arXiv
        </a>
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <FileText size={14} />
            PDF
          </a>
        )}
        {user && (
          <>
            <button
              onClick={() => isSaved ? unsave.mutate(paper.id) : save.mutate(paper.id)}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                isSaved
                  ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                  : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
              }`}
            >
              <Bookmark size={14} fill={isSaved ? "currentColor" : "none"} />
              {isSaved ? "Saved" : "Save"}
            </button>
            <div className="relative">
              <button
                onClick={() => setShowTagPicker(!showTagPicker)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <TagIcon size={14} />
                Tag
              </button>
              {showTagPicker && (
                <TagPicker paperId={paper.id} onClose={() => setShowTagPicker(false)} />
              )}
            </div>
            <div className="relative">
              <button
                onClick={() => setShowCollectionPicker(!showCollectionPicker)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <FolderPlus size={14} />
                Add to Collection
              </button>
              {showCollectionPicker && (
                <CollectionPicker paperId={paper.id} onClose={() => setShowCollectionPicker(false)} />
              )}
            </div>
          </>
        )}
      </div>

      <div className="prose dark:prose-invert max-w-none">
        <h2 className="text-lg font-semibold mb-2">Abstract</h2>
        <LaTeXText as="p" text={paper.summary} className="text-gray-700 dark:text-gray-300 leading-relaxed" />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Citations & References</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          View citations and references on external services:
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href={`https://www.semanticscholar.org/search?q=arXiv:${paper.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <BookOpen size={14} />
            Semantic Scholar
          </a>
          <a
            href={`https://scholar.google.com/scholar?q=arXiv:${paper.id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <GraduationCap size={14} />
            Google Scholar
          </a>
          <a
            href={`https://www.connectedpapers.com/main/${paper.id}/arxiv`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <Network size={14} />
            Connected Papers
          </a>
        </div>
      </div>

      {similar && similar.papers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Similar Papers</h2>
          <div className="space-y-3">
            {similar.papers.slice(0, 10).map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        </div>
      )}

      {authorPapers && authorPapers.papers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">More from These Authors</h2>
          <div className="space-y-3">
            {authorPapers.papers.slice(0, 8).map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
