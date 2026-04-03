import { Paper } from "@/types";
import PaperCard from "./PaperCard";

interface PaperListProps {
  papers: Paper[];
  loading?: boolean;
  onSave?: (id: string) => void;
  onTag?: (id: string) => void;
  savedIds?: Set<string>;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export default function PaperList({
  papers,
  loading,
  onSave,
  onTag,
  savedIds,
  onLoadMore,
  hasMore,
}: PaperListProps) {
  if (loading && papers.length === 0) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 animate-pulse"
          >
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3" />
            <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-full" />
              <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-5/6" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!loading && papers.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 dark:text-gray-500">
        <p className="text-lg">No papers found</p>
        <p className="text-sm mt-1">Try adjusting your search or filters</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {papers.map((paper) => (
        <PaperCard
          key={paper.id}
          paper={paper}
          onSave={onSave}
          onTag={onTag}
          saved={savedIds?.has(paper.id)}
        />
      ))}
      {hasMore && onLoadMore && (
        <button
          onClick={onLoadMore}
          disabled={loading}
          className="w-full py-3 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950 rounded-xl border border-gray-200 dark:border-gray-800 transition-colors disabled:opacity-50"
        >
          {loading ? "Loading..." : "Load more"}
        </button>
      )}
    </div>
  );
}
