import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ChevronDown } from "lucide-react";
import { useTagPapers } from "@/hooks/useTags";
import { useRecommendations } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";

const PAGE_SIZE = 10;

export default function TagDetailPage() {
  const { id } = useParams<{ id: string }>();
  const tagId = id ? parseInt(id, 10) : null;
  const { data: tagPapers, isLoading: loadingTagged } = useTagPapers(tagId);
  const { data: recs, isLoading: loadingRecs } = useRecommendations("tag", tagId ?? undefined);
  const [showTagged, setShowTagged] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const taggedPapers = tagPapers?.papers ?? [];
  const visibleTagged = useMemo(
    () => taggedPapers.slice(0, visibleCount),
    [taggedPapers, visibleCount],
  );

  return (
    <div className="space-y-6">
      <Link
        to="/tags"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600 dark:hover:text-brand-400"
      >
        <ArrowLeft size={14} />
        All tags
      </Link>

      <div>
        <h1 className="text-2xl font-bold mb-1">
          {tagPapers?.tag_name ?? "Tag"}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Recommendations based on {taggedPapers.length} tagged paper{taggedPapers.length !== 1 ? "s" : ""}
        </p>
      </div>

      <PaperList
        papers={recs?.papers ?? []}
        loading={loadingRecs}
        toolbar
      />

      {!loadingRecs && (!recs || recs.papers.length === 0) && taggedPapers.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400 py-4">
          Tag some papers to get recommendations here.
        </p>
      )}

      {taggedPapers.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
          <button
            onClick={() => setShowTagged(!showTagged)}
            className="flex items-center gap-2 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          >
            <ChevronDown
              size={16}
              className={`transition-transform ${showTagged ? "rotate-180" : ""}`}
            />
            Tagged papers ({taggedPapers.length})
          </button>
          {showTagged && (
            <div className="mt-3">
              <PaperList
                papers={visibleTagged}
                loading={loadingTagged}
                hasMore={taggedPapers.length > visibleCount}
                onLoadMore={() => setVisibleCount((c) => c + PAGE_SIZE)}
                toolbar
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
