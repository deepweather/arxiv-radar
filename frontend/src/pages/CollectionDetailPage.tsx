import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Globe, Lock } from "lucide-react";
import { useCollection } from "@/hooks/useCollections";
import PaperCard from "@/components/papers/PaperCard";
import { Paper } from "@/types";

export default function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useCollection(id!);

  if (isLoading) {
    return <div className="animate-pulse h-40 bg-gray-100 dark:bg-gray-800 rounded-xl" />;
  }

  if (!data) {
    return <div className="text-gray-500">Collection not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link
        to="/collections"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600"
      >
        <ArrowLeft size={14} />
        Back to collections
      </Link>

      <div>
        <div className="flex items-center gap-2">
          {data.is_public ? (
            <Globe size={16} className="text-green-500" />
          ) : (
            <Lock size={16} className="text-gray-400" />
          )}
          <h1 className="text-2xl font-bold">{data.name}</h1>
        </div>
        {data.description && (
          <p className="mt-1 text-gray-500 dark:text-gray-400">{data.description}</p>
        )}
      </div>

      <div className="space-y-3">
        {data.papers?.length > 0 ? (
          data.papers.map((p: Paper) => <PaperCard key={p.id} paper={p} />)
        ) : (
          <p className="text-center py-8 text-gray-400">No papers in this collection yet.</p>
        )}
      </div>
    </div>
  );
}
