import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useTagPapers } from "@/hooks/useTags";
import { useRecommendations } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";

const PAGE_SIZE = 10;

export default function TagDetailPage() {
  const { id } = useParams<{ id: string }>();
  const tagId = id ? parseInt(id, 10) : null;
  const { data: tagPapers, isLoading } = useTagPapers(tagId);
  const { data: recs } = useRecommendations("tag", tagId ?? undefined);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const allPapers = tagPapers?.papers ?? [];
  const visiblePapers = useMemo(
    () => allPapers.slice(0, visibleCount),
    [allPapers, visibleCount],
  );
  const hasMore = allPapers.length > visibleCount;

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
          {allPapers.length} paper{allPapers.length !== 1 ? "s" : ""}
        </p>
      </div>

      <PaperList
        papers={visiblePapers}
        loading={isLoading}
        hasMore={hasMore}
        onLoadMore={() => setVisibleCount((c) => c + PAGE_SIZE)}
      />

      {recs && recs.papers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">
            Recommended papers
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
            Similar to papers in this tag
          </p>
          <PaperList papers={recs.papers.slice(0, 10)} />
        </div>
      )}
    </div>
  );
}
