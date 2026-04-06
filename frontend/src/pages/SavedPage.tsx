import { Link } from "react-router-dom";
import { useSavedPapers } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";
import PaperList from "@/components/papers/PaperList";
import { Paper } from "@/types";

export default function SavedPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useSavedPapers();

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
      />
    </div>
  );
}
