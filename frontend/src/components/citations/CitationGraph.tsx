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
      <div className="animate-pulse h-32 bg-gray-100 dark:bg-gray-800 rounded-xl" />
    );
  }

  if (!data || (data.citing.length === 0 && data.cited_by.length === 0)) {
    return (
      <p className="text-sm text-gray-400 py-4">No citation data available.</p>
    );
  }

  return (
    <div className="space-y-6">
      {data.cited_by.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">
            Cited by ({data.cited_by.length})
          </h3>
          <div className="space-y-2">
            {data.cited_by.slice(0, 15).map((p, i) => (
              <CitPaperRow key={i} paper={p} />
            ))}
          </div>
        </div>
      )}

      {data.citing.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">
            References ({data.citing.length})
          </h3>
          <div className="space-y-2">
            {data.citing.slice(0, 15).map((p, i) => (
              <CitPaperRow key={i} paper={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CitPaperRow({ paper }: { paper: CitPaper }) {
  const url = paper.arxiv_id
    ? `/paper/${paper.arxiv_id}`
    : null;

  return (
    <div className="px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          {url ? (
            <a href={url} className="font-medium hover:text-brand-600 dark:hover:text-brand-400 leading-snug">
              {paper.title}
            </a>
          ) : (
            <span className="font-medium leading-snug">{paper.title}</span>
          )}
          <p className="text-xs text-gray-400 mt-0.5">
            {paper.authors.slice(0, 3).join(", ")}
            {paper.authors.length > 3 && " et al."}
            {paper.year && ` (${paper.year})`}
          </p>
        </div>
        {paper.citation_count != null && (
          <span className="shrink-0 text-xs text-gray-400">
            {paper.citation_count} cites
          </span>
        )}
      </div>
    </div>
  );
}
