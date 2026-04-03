import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, ChevronRight } from "lucide-react";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/useTags";
import { useRecommendations } from "@/hooks/usePapers";
import PaperList from "@/components/papers/PaperList";
import { useAuthStore } from "@/stores/authStore";

export default function TagsPage() {
  const user = useAuthStore((s) => s.user);
  const { data: tags, isLoading } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();
  const [newTag, setNewTag] = useState("");
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const { data: recs } = useRecommendations("tag", selectedTagId ?? undefined);

  if (!user) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-2">Tags</h1>
        <p className="text-gray-500 dark:text-gray-400">
          <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link> to manage tags
        </p>
      </div>
    );
  }

  const handleCreate = () => {
    if (!newTag.trim()) return;
    createTag.mutate(newTag.trim(), { onSuccess: () => setNewTag("") });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Tags</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Tag papers and get personalized recommendations based on your interests
        </p>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="New tag name..."
          value={newTag}
          onChange={(e) => setNewTag(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={handleCreate}
          disabled={createTag.isPending}
          className="px-4 py-2.5 rounded-xl bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          <Plus size={16} />
          Create
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {isLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-16 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
            ))
          : (tags ?? []).map((tag) => (
              <button
                key={tag.id}
                type="button"
                aria-pressed={selectedTagId === tag.id}
                className={`flex items-center justify-between p-4 rounded-xl border transition-colors text-left w-full ${
                  selectedTagId === tag.id
                    ? "border-brand-400 bg-brand-50 dark:bg-brand-950 dark:border-brand-700"
                    : "border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-brand-300"
                }`}
                onClick={() => setSelectedTagId(selectedTagId === tag.id ? null : tag.id)}
              >
                <div>
                  <span className="font-medium">{tag.name}</span>
                  <span className="ml-2 text-sm text-gray-400">{tag.paper_count} papers</span>
                </div>
                <div className="flex items-center gap-1">
                  <span
                    role="button"
                    tabIndex={0}
                    aria-label={`Delete tag ${tag.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete tag "${tag.name}"?`)) deleteTag.mutate(tag.id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        if (confirm(`Delete tag "${tag.name}"?`)) deleteTag.mutate(tag.id);
                      }
                    }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                  >
                    <Trash2 size={14} />
                  </span>
                  <ChevronRight size={14} className="text-gray-400" />
                </div>
              </button>
            ))}
      </div>

      {selectedTagId && recs && (
        <div>
          <h2 className="text-lg font-semibold mb-3">
            Recommended papers for this tag
          </h2>
          <PaperList papers={recs.papers} />
        </div>
      )}
    </div>
  );
}
