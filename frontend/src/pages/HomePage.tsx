import { usePapers } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";
import SearchBar from "@/components/search/SearchBar";
import { Paper } from "@/types";

export default function HomePage() {
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    usePapers({ limit: 25 });

  const papers: Paper[] = data?.pages.flatMap((p) => p.papers) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Recent Papers</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Latest papers from arXiv in ML, CV, NLP, AI, and Robotics
        </p>
      </div>

      <SearchBar />

      <PaperList
        papers={papers}
        loading={isLoading || isFetchingNextPage}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
      />
    </div>
  );
}
