import { Link } from "react-router-dom";
import { useSavedPapers, useUnsavePaper } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";
import PaperList from "@/components/papers/PaperList";
import { Paper } from "@/types";

export default function SavedPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useSavedPapers();
  const unsave = useUnsavePaper();

  if (!user) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-2">Saved Papers</h1>
        <p className="text-gray-500 dark:text-gray-400">
          <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link> to save papers
        </p>
      </div>
    );
  }

  const papers: Paper[] = data?.papers ?? [];
  const savedIds = new Set(papers.map((p) => p.id));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Saved Papers</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Your reading list
        </p>
      </div>

      <PaperList
        papers={papers}
        loading={isLoading}
        savedIds={savedIds}
        onSave={(id) => unsave.mutate(id)}
      />
    </div>
  );
}
