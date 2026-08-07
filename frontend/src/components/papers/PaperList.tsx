import { useState, useMemo } from "react";
import React from "react";
import { Search, ArrowUpDown } from "lucide-react";
import { Paper } from "@/types";
import PaperCard from "./PaperCard";

type SortKey = "newest" | "oldest" | "title";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "title", label: "Title A–Z" },
];

function sortPapers(papers: Paper[], key: SortKey): Paper[] {
  const sorted = [...papers];
  switch (key) {
    case "newest":
      return sorted.sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""));
    case "oldest":
      return sorted.sort((a, b) => (a.published_at ?? "").localeCompare(b.published_at ?? ""));
    case "title":
      return sorted.sort((a, b) => a.title.localeCompare(b.title));
  }
}

function filterPapers(papers: Paper[], query: string): Paper[] {
  if (!query) return papers;
  const q = query.toLowerCase();
  return papers.filter(
    (p) =>
      p.title.toLowerCase().includes(q) ||
      p.authors.some((a) => a.name.toLowerCase().includes(q)) ||
      p.categories.some((c) => c.toLowerCase().includes(q)),
  );
}

interface PaperListProps {
  papers: Paper[];
  loading?: boolean;
  onTag?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  toolbar?: boolean;
  selectable?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (paperId: string) => void;
  onSelectAllVisible?: (visibleIds: string[]) => void;
  onClearSelection?: () => void;
  downloadAction?: React.ReactNode;
}

export default function PaperList({
  papers,
  loading,
  onTag,
  onLoadMore,
  hasMore,
  toolbar,
  selectable,
  selectedIds,
  onToggleSelect,
  onSelectAllVisible,
  onClearSelection,
  downloadAction,
}: PaperListProps) {
  const [sort, setSort] = useState<SortKey>("newest");
  const [search, setSearch] = useState("");

  const processed = useMemo(() => {
    if (!toolbar) return papers;
    return sortPapers(filterPapers(papers, search), sort);
  }, [papers, toolbar, sort, search]);

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
      {toolbar && papers.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[180px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Filter by title, author, category…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-brand-500 placeholder:text-gray-400"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <ArrowUpDown size={14} className="text-gray-400" />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="px-2.5 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-brand-500"
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          {search && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {processed.length} of {papers.length}
            </span>
          )}
        </div>
      )}
      {selectable && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onSelectAllVisible?.(processed.map((p) => p.id))}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Select all {processed.length}
          </button>
          {selectedIds && selectedIds.size > 0 && (
            <button
              onClick={() => onClearSelection?.()}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Clear ({selectedIds.size})
            </button>
          )}
          {downloadAction && <div className="ml-auto">{downloadAction}</div>}
        </div>
      )}
      {processed.map((paper) => (
        <PaperCard
          key={paper.id}
          paper={paper}
          onTag={onTag}
          selectable={selectable}
          selected={selectedIds?.has(paper.id) ?? false}
          onToggleSelect={onToggleSelect}
        />
      ))}
      {toolbar && search && processed.length === 0 && (
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <p className="text-sm">No papers match "{search}"</p>
        </div>
      )}
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
