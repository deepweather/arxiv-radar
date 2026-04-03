import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2, Globe, Lock } from "lucide-react";
import { useCollections, useCreateCollection, useDeleteCollection } from "@/hooks/useCollections";
import { useAuthStore } from "@/stores/authStore";

export default function CollectionsPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useCollections();
  const create = useCreateCollection();
  const del = useDeleteCollection();
  const [name, setName] = useState("");

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Collections</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Organize papers into curated reading lists
        </p>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          placeholder="New collection name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && name.trim() && create.mutate({ name: name.trim() }, { onSuccess: () => setName("") })}
          className="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={() => name.trim() && create.mutate({ name: name.trim() }, { onSuccess: () => setName("") })}
          disabled={create.isPending}
          className="px-4 py-2.5 rounded-xl bg-brand-600 text-white font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          <Plus size={16} />
          Create
        </button>
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
