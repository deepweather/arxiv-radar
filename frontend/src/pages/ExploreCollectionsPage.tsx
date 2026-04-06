import { useState } from "react";
import { Link } from "react-router-dom";
import { Globe, Eye, FileText, TrendingUp, Star, Clock } from "lucide-react";
import { usePublicCollections } from "@/hooks/useCollections";
import { Collection } from "@/types";

const SORT_OPTIONS = [
  { value: "trending", label: "Trending", icon: TrendingUp },
  { value: "popular", label: "Popular", icon: Star },
  { value: "recent", label: "Recent", icon: Clock },
] as const;

export default function ExploreCollectionsPage() {
  const [sort, setSort] = useState("trending");
  const { data, isLoading } = usePublicCollections(sort);
  const collections = data?.collections ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Explore Collections</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Discover curated paper collections shared by the community
        </p>
      </div>

      <div className="flex gap-2">
        {SORT_OPTIONS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            onClick={() => setSort(value)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              sort === value
                ? "bg-brand-600 text-white"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
            ))
          : collections.map((c: Collection) => (
              <Link
                key={c.id}
                to={`/collections/${c.id}`}
                className="block p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Globe size={14} className="text-green-500 shrink-0" />
                      <span className="font-medium truncate">{c.name}</span>
                    </div>
                    {c.description && (
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                        {c.description}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500">
                      <span>by {c.owner_name}</span>
                      <span className="flex items-center gap-1">
                        <FileText size={12} />
                        {c.paper_count ?? 0} papers
                      </span>
                      <span className="flex items-center gap-1">
                        <Eye size={12} />
                        {c.view_count ?? 0} views
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
        {!isLoading && collections.length === 0 && (
          <div className="text-center py-12">
            <Globe size={40} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-gray-500 dark:text-gray-400">
              No public collections yet. Be the first to share one!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
