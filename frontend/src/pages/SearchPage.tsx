import { useSearchParams } from "react-router-dom";
import { usePapers } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";
import SearchBar from "@/components/search/SearchBar";
import { Paper } from "@/types";

export default function SearchPage() {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") || "";

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    usePapers({ q, limit: 25 });

  const papers: Paper[] = data?.pages.flatMap((p) => p.papers) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Search</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Semantic + keyword hybrid search across all papers
        </p>
      </div>

      <SearchBar />

      {q && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Results for <span className="font-medium text-gray-700 dark:text-gray-300">"{q}"</span>
        </p>
      )}

      <PaperList
        papers={papers}
        loading={isLoading || isFetchingNextPage}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
      />
    </div>
  );
}
