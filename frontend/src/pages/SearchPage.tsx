import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { EyeOff } from "lucide-react";
import { usePapers } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";
import { useAuthStore } from "@/stores/authStore";
import { Paper } from "@/types";

const CATEGORIES = ["cs.CV", "cs.LG", "cs.CL", "cs.AI", "cs.NE", "cs.RO"];

const SORT_OPTIONS = [
  { value: "relevance", label: "Most Relevant" },
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
] as const;

const DATE_OPTIONS = [
  { value: undefined, label: "All Time" },
  { value: 7, label: "Past Week" },
  { value: 30, label: "Past Month" },
  { value: 365, label: "Past Year" },
] as const;

export default function SearchPage() {
  const user = useAuthStore((s) => s.user);
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") || "";
  const catsFromUrl = searchParams.get("categories");
  const [selectedCats, setSelectedCats] = useState<string[]>(
    catsFromUrl ? catsFromUrl.split(",").map((c) => c.trim()) : [],
  );
  const [sort, setSort] = useState<string>("relevance");
  const [days, setDays] = useState<number | undefined>(undefined);
  const [hideTagged, setHideTagged] = useState(false);

  const catParam = selectedCats.length > 0 ? selectedCats.join(",") : undefined;
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    usePapers({ 
      q, 
      limit: 25, 
      categories: catParam, 
      sort: sort !== "relevance" || !q ? sort : undefined, 
      days,
      excludeTagged: user && hideTagged ? true : undefined,
    });

  const papers: Paper[] = data?.pages.flatMap((p) => p.papers) ?? [];

  const toggleCat = (cat: string) => {
    setSelectedCats((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
    );
  };

  return (
    <div className="space-y-6">
      <Helmet>
        <title>{q ? `${q} - arxiv radar` : "Search - arxiv radar"}</title>
      </Helmet>
      <div>
        <h1 className="text-2xl font-bold mb-1">Search</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Semantic + keyword hybrid search across all papers
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="sort" className="text-xs text-gray-500 dark:text-gray-400">Sort:</label>
          <select
            id="sort"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-brand-500 outline-none"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="dateRange" className="text-xs text-gray-500 dark:text-gray-400">Date:</label>
          <select
            id="dateRange"
            value={days ?? ""}
            onChange={(e) => setDays(e.target.value ? Number(e.target.value) : undefined)}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:ring-2 focus:ring-brand-500 outline-none"
          >
            {DATE_OPTIONS.map((opt) => (
              <option key={opt.label} value={opt.value ?? ""}>{opt.label}</option>
            ))}
          </select>
        </div>
        {user && (
          <button
            onClick={() => setHideTagged(!hideTagged)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
              hideTagged
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            }`}
          >
            <EyeOff size={12} />
            Hide tagged
          </button>
        )}
      </div>

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
        onTag={!!user}
      />
    </div>
  );
}
