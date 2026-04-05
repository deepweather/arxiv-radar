import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, ChevronRight } from "lucide-react";
import { useTags, useCreateTag, useDeleteTag } from "@/hooks/useTags";
import { useAuthStore } from "@/stores/authStore";

export default function TagsPage() {
  const user = useAuthStore((s) => s.user);
  const { data: tags, isLoading } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();
  const [newTag, setNewTag] = useState("");

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
              <div
                key={tag.id}
                className="flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
              >
                <Link
                  to={`/tags/${tag.id}`}
                  className="flex-1 min-w-0"
                >
                  <span className="font-medium">{tag.name}</span>
                  <span className="ml-2 text-sm text-gray-400">{tag.paper_count} papers</span>
                </Link>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    aria-label={`Delete tag ${tag.name}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete tag "${tag.name}"?`)) deleteTag.mutate(tag.id);
                    }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                  <Link to={`/tags/${tag.id}`} className="p-1.5 text-gray-400">
                    <ChevronRight size={14} />
                  </Link>
                </div>
              </div>
            ))}
      </div>

      {!isLoading && (tags ?? []).length === 0 && (
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <p>No tags yet. Create one above, then tag papers from the home page.</p>
        </div>
      )}
    </div>
  );
}
