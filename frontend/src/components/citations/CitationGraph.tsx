import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, ChevronDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";

interface CitationData {
  citing: CitPaper[];
  cited_by: CitPaper[];
  error: string | null;
}

interface CitPaper {
  title: string;
  authors: string[];
  year: number | null;
  arxiv_id: string | null;
  citation_count: number | null;
}

interface Props {
  paperId: string;
}

const COLLAPSED_LIMIT = 5;

export default function CitationGraph({ paperId }: Props) {
  const { data, isLoading } = useQuery<CitationData>({
    queryKey: ["citations", paperId],
    queryFn: async () => {
      const { data } = await api.get(`/social/citations/${paperId}`);
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="animate-pulse h-10 bg-gray-100 dark:bg-gray-800 rounded-lg" />
    );
  }

  if (!data || (data.citing.length === 0 && data.cited_by.length === 0)) {
    return (
      <p className="text-sm text-gray-400 py-2">Citation data is being fetched. Check back soon.</p>
    );
  }

  return (
    <div className="space-y-1">
      {data.cited_by.length > 0 && (
        <CitationSection label="Cited by" count={data.cited_by.length} papers={data.cited_by} />
      )}
      {data.citing.length > 0 && (
        <CitationSection label="References" count={data.citing.length} papers={data.citing} />
      )}
    </div>
  );
}

function CitationSection({ label, count, papers }: { label: string; count: number; papers: CitPaper[] }) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const visible = open ? (showAll ? papers : papers.slice(0, COLLAPSED_LIMIT)) : [];
  const hasMore = papers.length > COLLAPSED_LIMIT;

  return (
    <div>
      <button
        onClick={() => { setOpen(!open); if (!open) setShowAll(false); }}
        className="flex items-center gap-1.5 w-full px-2 py-2 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {label} ({count})
      </button>

      {open && (
        <div className="ml-5 space-y-1 pb-2">
          {visible.map((p, i) => (
            <CitPaperRow key={i} paper={p} />
          ))}
          {hasMore && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              className="text-xs text-brand-600 dark:text-brand-400 hover:underline px-2 py-1"
            >
              Show all {count}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function CitPaperRow({ paper }: { paper: CitPaper }) {
  const title = (
    <span className="font-medium leading-snug hover:text-brand-600 dark:hover:text-brand-400">
      {paper.title}
    </span>
  );

  return (
    <div className="px-2 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/30 text-sm flex items-start justify-between gap-2">
      <div className="min-w-0">
        {paper.arxiv_id ? (
          <Link to={`/paper/${paper.arxiv_id}`}>{title}</Link>
        ) : (
          <span className="text-gray-700 dark:text-gray-300">{title}</span>
        )}
        <p className="text-xs text-gray-400 mt-0.5 truncate">
          {paper.authors.slice(0, 3).join(", ")}
          {paper.authors.length > 3 && " et al."}
          {paper.year && ` (${paper.year})`}
        </p>
      </div>
      {paper.citation_count != null && paper.citation_count > 0 && (
        <span className="shrink-0 text-xs text-gray-400 tabular-nums pt-0.5">
          {paper.citation_count} cites
        </span>
      )}
    </div>
  );
}
