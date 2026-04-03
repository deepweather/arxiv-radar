import { useParams, Link } from "react-router-dom";
import { ExternalLink, FileText, ArrowLeft } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { usePaper, useSimilarPapers } from "@/hooks/usePapers";
import PaperCard from "@/components/papers/PaperCard";
import CitationGraph from "@/components/citations/CitationGraph";

export default function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: paper, isLoading } = usePaper(id!);
  const { data: similar } = useSimilarPapers(id!);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        <div className="space-y-2 mt-6">
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded" />
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded" />
          <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-4/5" />
        </div>
      </div>
    );
  }

  if (!paper) {
    return <div className="text-gray-500">Paper not found.</div>;
  }

  const authorStr = paper.authors.map((a) => a.name).join(", ");
  const timeAgo = paper.published_at
    ? formatDistanceToNow(new Date(paper.published_at), { addSuffix: true })
    : "";

  return (
    <div className="space-y-8">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600 dark:hover:text-brand-400"
      >
        <ArrowLeft size={14} />
        Back
      </Link>

      <div>
        <h1 className="text-2xl font-bold leading-tight">{paper.title}</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{authorStr}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-gray-400">{timeAgo}</span>
          {paper.categories.map((cat) => (
            <span
              key={cat}
              className="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
            >
              {cat}
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-3">
        <a
          href={`https://arxiv.org/abs/${paper.id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <ExternalLink size={14} />
          View on arXiv
        </a>
        {paper.pdf_url && (
          <a
            href={paper.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <FileText size={14} />
            PDF
          </a>
        )}
      </div>

      <div className="prose dark:prose-invert max-w-none">
        <h2 className="text-lg font-semibold mb-2">Abstract</h2>
        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{paper.summary}</p>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">Citations</h2>
        <CitationGraph paperId={paper.id} />
      </div>

      {similar && similar.papers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Similar Papers</h2>
          <div className="space-y-3">
            {similar.papers.slice(0, 10).map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
