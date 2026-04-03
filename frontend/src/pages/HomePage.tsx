import { useState } from "react";
import { EyeOff } from "lucide-react";
import { usePapers, useRecommendations } from "@/hooks/usePapers";
import { useSavePaper, useUnsavePaper, useSavedPapers } from "@/hooks/useCollections";
import PaperList from "@/components/papers/PaperList";
import { useAuthStore } from "@/stores/authStore";
import { Paper } from "@/types";

const CATEGORIES = ["cs.CV", "cs.LG", "cs.CL", "cs.AI", "cs.NE", "cs.RO"];

type TabType = "for-you" | "recent" | "random";

export default function HomePage() {
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<TabType>(user ? "for-you" : "recent");
  const [selectedCats, setSelectedCats] = useState<string[]>([]);
  const [hideTagged, setHideTagged] = useState(false);

  const catParam = selectedCats.length > 0 ? selectedCats.join(",") : undefined;
  const sortParam = tab === "random" ? "random" : undefined;
  const recentQuery = usePapers({ 
    limit: 25, 
    categories: catParam, 
    sort: sortParam,
    excludeTagged: user && hideTagged ? true : undefined,
  });
  const forYouQuery = useRecommendations("for-you");

  const save = useSavePaper();
  const unsave = useUnsavePaper();
  const { data: savedData } = useSavedPapers();
  const savedIds = new Set<string>((savedData?.papers ?? []).map((p: Paper) => p.id));

  const recentPapers: Paper[] = recentQuery.data?.pages.flatMap((p) => p.papers) ?? [];
  const forYouPapers: Paper[] = forYouQuery.data?.papers ?? [];

  const showForYou = user && tab === "for-you";
  const showRandom = tab === "random";
  const papers = showForYou ? forYouPapers : recentPapers;
  const isLoading = showForYou ? forYouQuery.isLoading : (recentQuery.isLoading || recentQuery.isFetchingNextPage);
  const hasForYouContent = forYouPapers.length > 0;

  const toggleCat = (cat: string) => {
    setSelectedCats((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat],
    );
  };

  const handleSave = (id: string) => {
    if (savedIds.has(id)) unsave.mutate(id);
    else save.mutate(id);
  };

  const getTitle = () => {
    if (showForYou) return "For You";
    if (showRandom) return "Random Discovery";
    return "Recent Papers";
  };

  const getSubtitle = () => {
    if (showForYou) return "Personalized recommendations based on your tags";
    if (showRandom) return "Discover papers serendipitously";
    return "Latest papers from arXiv in ML, CV, NLP, AI, and Robotics";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">{getTitle()}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">{getSubtitle()}</p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex gap-2">
          {user && (
            <button
              onClick={() => setTab("for-you")}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                tab === "for-you"
                  ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                  : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              For You
            </button>
          )}
          <button
            onClick={() => setTab("recent")}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              tab === "recent"
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            Recent
          </button>
          <button
            onClick={() => setTab("random")}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              tab === "random"
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            Random
          </button>
        </div>
        
        {user && (
          <button
            onClick={() => setHideTagged(!hideTagged)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              hideTagged
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
            }`}
            title={showForYou ? "For You recommendations are already personalized based on your tags" : undefined}
          >
            <EyeOff size={14} />
            Hide tagged
          </button>
        )}
      </div>

      {!showForYou && (
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
      )}

      {showForYou && !isLoading && !hasForYouContent && (
        <div className="text-center py-12 space-y-2">
          <p className="text-gray-500 dark:text-gray-400">
            Tag some papers to get personalized recommendations.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Go to any paper and use the Tag button, or visit the Tags page to get started.
          </p>
        </div>
      )}

      {(!showForYou || hasForYouContent) && (
        <PaperList
          papers={papers}
          loading={isLoading}
          hasMore={!showForYou && !showRandom ? recentQuery.hasNextPage : undefined}
          onLoadMore={!showForYou && !showRandom ? () => recentQuery.fetchNextPage() : undefined}
          onSave={user ? handleSave : undefined}
          onTag={!!user}
          savedIds={savedIds}
        />
      )}
    </div>
  );
}
