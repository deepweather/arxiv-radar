import { useState, useRef, useEffect } from "react";
import { Plus, X, Check } from "lucide-react";
import { useCollections, useCreateCollection, useAddToCollection } from "@/hooks/useCollections";

interface CollectionPickerProps {
  paperId: string;
  onClose: () => void;
}

export default function CollectionPicker({ paperId, onClose }: CollectionPickerProps) {
  const { data } = useCollections();
  const collections = data?.collections ?? [];
  const createCollection = useCreateCollection();
  const addToCollection = useAddToCollection();
  const [newName, setNewName] = useState("");
  const [filter, setFilter] = useState("");
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const filtered = collections.filter((c) =>
    c.name.toLowerCase().includes(filter.toLowerCase()),
  );

  const handleAdd = (collectionId: string) => {
    addToCollection.mutate(
      { collectionId, paperId },
      {
        onSuccess: () => {
          setAddedIds((prev) => new Set(prev).add(collectionId));
        },
      }
    );
  };

  const handleCreate = () => {
    if (!newName.trim()) return;
    createCollection.mutate(
      { name: newName.trim() },
      {
        onSuccess: (data) => {
          addToCollection.mutate(
            { collectionId: data.id, paperId },
            {
              onSuccess: () => {
                setAddedIds((prev) => new Set(prev).add(data.id));
              },
            }
          );
          setNewName("");
        },
      }
    );
  };

  return (
    <div
      ref={ref}
      className="absolute top-full left-0 z-50 mt-1 w-64 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xl p-2"
    >
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs font-medium text-gray-500">Add to collection</span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X size={14} />
        </button>
      </div>
      <input
        type="text"
        placeholder="Filter collections..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-1 focus:ring-brand-500 mb-1"
        autoFocus
      />
      <div className="max-h-40 overflow-y-auto space-y-0.5">
        {filtered.length === 0 && (
          <p className="px-2 py-1.5 text-sm text-gray-400">No collections yet</p>
        )}
        {filtered.map((collection) => {
          const isAdded = addedIds.has(collection.id);
          return (
            <button
              key={collection.id}
              onClick={() => !isAdded && handleAdd(collection.id)}
              disabled={isAdded}
              className={`w-full text-left px-2 py-1.5 text-sm rounded-lg transition-colors flex items-center justify-between ${
                isAdded
                  ? "bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-400"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <span className="truncate">{collection.name}</span>
              {isAdded ? (
                <Check size={14} className="flex-shrink-0 ml-2" />
              ) : (
                <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                  ({collection.paper_count})
                </span>
              )}
            </button>
          );
        })}
      </div>
      <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800">
        <div className="flex gap-1">
          <input
            type="text"
            placeholder="New collection..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            className="flex-1 px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none"
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim() || createCollection.isPending}
            className="p-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
