import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { usePapers } from "@/hooks/usePapers";
import { useSavePaper, useUnsavePaper, useSavedPapers } from "@/hooks/useCollections";
import PaperList from "@/components/papers/PaperList";
import SearchBar from "@/components/search/SearchBar";
import { useAuthStore } from "@/stores/authStore";
import { Paper } from "@/types";

const CATEGORIES = ["cs.CV", "cs.LG", "cs.CL", "cs.AI", "cs.NE", "cs.RO"];

export default function SearchPage() {
  const user = useAuthStore((s) => s.user);
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") || "";
  const catsFromUrl = searchParams.get("categories");
  const [selectedCats, setSelectedCats] = useState<string[]>(
    catsFromUrl ? catsFromUrl.split(",").map((c) => c.trim()) : [],
  );

  const catParam = selectedCats.length > 0 ? selectedCats.join(",") : undefined;
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    usePapers({ q, limit: 25, categories: catParam });

  const save = useSavePaper();
  const unsave = useUnsavePaper();
  const { data: savedData } = useSavedPapers();
  const savedIds = new Set<string>((savedData?.papers ?? []).map((p: Paper) => p.id));

  const papers: Paper[] = data?.pages.flatMap((p) => p.papers) ?? [];

  const toggleCat = (cat: string) => {
    setSelectedCats((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
    );
  };

  const handleSave = (id: string) => {
    if (savedIds.has(id)) unsave.mutate(id);
    else save.mutate(id);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Search</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Semantic + keyword hybrid search across all papers
        </p>
      </div>

      <SearchBar />

      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => toggleCat(cat)}
            aria-pressed={selectedCats.includes(cat)}
            className={`px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
              selectedCats.includes(cat)
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

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
        onSave={user ? handleSave : undefined}
        onTag={!!user}
        savedIds={savedIds}
      />
    </div>
  );
}
