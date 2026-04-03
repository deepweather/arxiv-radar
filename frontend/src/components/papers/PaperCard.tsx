import { useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, ExternalLink, Tag as TagIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Paper } from "@/types";
import TagPicker from "@/components/tags/TagPicker";
import LaTeXText from "@/components/common/LaTeXText";

interface PaperCardProps {
  paper: Paper;
  onSave?: (id: string) => void;
  onTag?: boolean;
  saved?: boolean;
}

export default function PaperCard({ paper, onSave, onTag, saved }: PaperCardProps) {
  const [showTagPicker, setShowTagPicker] = useState(false);
  const authorStr = paper.authors.map((a) => a.name).join(", ");
  const timeAgo = paper.published_at
    ? formatDistanceToNow(new Date(paper.published_at), { addSuffix: true })
    : "";

  return (
    <article className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 hover:border-brand-300 dark:hover:border-brand-700 transition-colors">
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
          {onSave && (
            <button
              onClick={() => onSave(paper.id)}
              className={`p-1.5 rounded-lg transition-colors ${
                saved
                  ? "text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950"
                  : "text-gray-400 hover:text-brand-600 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
              aria-label={saved ? "Unsave from reading list" : "Save to reading list"}
            >
              <Bookmark size={16} fill={saved ? "currentColor" : "none"} />
            </button>
          )}
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
      <div className="mt-3 flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
        <span>{timeAgo}</span>
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
    </article>
  );
}
