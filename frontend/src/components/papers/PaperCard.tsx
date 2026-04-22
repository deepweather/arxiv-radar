import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bookmark, ExternalLink, Tag as TagIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Paper } from "@/types";
import { useAuthStore } from "@/stores/authStore";
import { useSavePaper, useUnsavePaper, useSavedPapers } from "@/hooks/useCollections";
import TagPicker from "@/components/tags/TagPicker";
import LaTeXText from "@/components/common/LaTeXText";

interface PaperCardProps {
  paper: Paper;
  onTag?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: (paperId: string) => void;
}

export default function PaperCard({ paper, onTag, selectable, selected, onToggleSelect }: PaperCardProps) {
  const [showTagPicker, setShowTagPicker] = useState(false);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const { data: savedData } = useSavedPapers();
  const save = useSavePaper();
  const unsave = useUnsavePaper();

  const savedIds = new Set<string>(
    (savedData?.papers ?? []).map((p: Paper) => p.id),
  );
  const isSaved = savedIds.has(paper.id);

  const handleSave = () => {
    if (!user) {
      navigate("/login");
      return;
    }
    if (isSaved) unsave.mutate(paper.id);
    else save.mutate(paper.id);
  };

  const authorStr = paper.authors.map((a) => a.name).join(", ");
  const timeAgo = paper.published_at
    ? formatDistanceToNow(new Date(paper.published_at), { addSuffix: true })
    : "";

  return (
    <article className={`bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:border-brand-300 dark:hover:border-brand-700 transition-colors${selected ? " ring-2 ring-brand-400" : ""}`}>
      <div className="flex items-start gap-3">
        {selectable && (
          <label className="p-2 -m-2 shrink-0 flex items-center mt-0.5 cursor-pointer">
            <input
              type="checkbox"
              checked={!!selected}
              onChange={() => onToggleSelect?.(paper.id)}
              aria-label={`Select paper: ${paper.title}`}
              className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
          </label>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <Link
                to={`/paper/${paper.id}`}
                className="text-base font-semibold text-gray-900 dark:text-gray-100 hover:text-brand-700 dark:hover:text-brand-400 leading-snug line-clamp-2"
              >
                <LaTeXText text={paper.title} />
              </Link>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-1">{authorStr}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={handleSave}
                className={`p-1.5 rounded-lg transition-colors ${
                  isSaved
                    ? "text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950"
                    : "text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
                aria-label={isSaved ? "Unsave from reading list" : "Save to reading list"}
              >
                <Bookmark size={16} fill={isSaved ? "currentColor" : "none"} />
              </button>
              {onTag && (
                <div className="relative">
                  <button
                    onClick={() => setShowTagPicker(!showTagPicker)}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    aria-label="Add tag"
                  >
                    <TagIcon size={16} />
                  </button>
                  {showTagPicker && (
                    <TagPicker paperId={paper.id} onClose={() => setShowTagPicker(false)} />
                  )}
                </div>
              )}
              <a
                href={`https://arxiv.org/abs/${paper.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                aria-label="View on arXiv (opens in new tab)"
              >
                <ExternalLink size={16} />
              </a>
            </div>
          </div>
          <LaTeXText
            as="p"
            text={paper.summary}
            className="mt-3 text-sm text-gray-600 dark:text-gray-300 line-clamp-3 leading-relaxed"
          />
          <div className="mt-3 flex items-center flex-wrap gap-2 text-xs text-gray-400 dark:text-gray-500">
            <span>{timeAgo}</span>
            {paper.user_tags && paper.user_tags.length > 0 && (
              <>
                {paper.user_tags.map((tag) => (
                  <Link
                    key={tag.id}
                    to={`/tags`}
                    className="px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 font-medium flex items-center gap-1"
                  >
                    <TagIcon size={10} />
                    {tag.name}
                  </Link>
                ))}
              </>
            )}
            {paper.categories.slice(0, 3).map((cat) => (
              <Link
                key={cat}
                to={`/search?categories=${cat}`}
                className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-950 dark:hover:text-brand-400 transition-colors"
              >
                {cat}
              </Link>
            ))}
            {(paper.score ?? paper.similarity) !== undefined && (
              <span className="ml-auto font-mono text-brand-600 dark:text-brand-400">
                {(paper.score ?? paper.similarity)?.toFixed(4)}
              </span>
            )}
          </div>
          {paper.similar_to && paper.similar_to.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
              <p className="text-xs text-gray-400 dark:text-gray-500">
                Similar to your tagged:{" "}
                {paper.similar_to.slice(0, 2).map((sp, i) => (
                  <span key={sp.id}>
                    {i > 0 && ", "}
                    <Link
                      to={`/paper/${sp.id}`}
                      className="text-brand-600 dark:text-brand-400 hover:underline"
                    >
                      {sp.title.length > 50 ? sp.title.slice(0, 50) + "..." : sp.title}
                    </Link>
                  </span>
                ))}
              </p>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
