import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, Globe, Lock, ChevronDown, ChevronUp } from "lucide-react";
import { useCollections, useCreateCollection, useDeleteCollection } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";

export default function CollectionsPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useCollections();
  const create = useCreateCollection();
  const del = useDeleteCollection();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  if (!user) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-2">Collections</h1>
        <p className="text-gray-500 dark:text-gray-400">
          <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link> to create collections
        </p>
      </div>
    );
  }

  const collections = data?.collections ?? [];

  const handleCreate = () => {
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), description: description.trim() || undefined, is_public: isPublic },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
          setIsPublic(false);
          setShowOptions(false);
        },
      },
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Collections</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Organize papers into curated reading lists
        </p>
      </div>

      <div className="space-y-2 p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="New collection name..."
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={handleCreate}
            disabled={create.isPending || !name.trim()}
            className="px-4 py-2.5 rounded-xl bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            <Plus size={16} />
            Create
          </button>
        </div>
        <button
          onClick={() => setShowOptions(!showOptions)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          {showOptions ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showOptions ? "Less options" : "More options"}
        </button>
        {showOptions && (
          <div className="space-y-2 pt-1">
            <input
              type="text"
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-2 focus:ring-brand-500 text-sm"
            />
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="rounded border-gray-300"
              />
              <Globe size={14} />
              Public collection
            </label>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
            ))
          : collections.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-brand-300 transition-colors"
              >
                <Link to={`/collections/${c.id}`} className="flex-1">
                  <div className="flex items-center gap-2">
                    {c.is_public ? (
                      <Globe size={14} className="text-green-500" />
                    ) : (
                      <Lock size={14} className="text-gray-400" />
                    )}
                    <span className="font-medium">{c.name}</span>
                    <span className="text-sm text-gray-400">{c.paper_count} papers</span>
                  </div>
                  {c.description && (
                    <p className="mt-1 text-sm text-gray-500 line-clamp-1">{c.description}</p>
                  )}
                </Link>
                <button
                  onClick={() => confirm(`Delete "${c.name}"?`) && del.mutate(c.id)}
                  className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
        {!isLoading && collections.length === 0 && (
          <p className="text-center py-8 text-gray-400">No collections yet. Create one above!</p>
        )}
      </div>
    </div>
  );
}
