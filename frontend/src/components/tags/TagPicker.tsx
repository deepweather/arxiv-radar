import { useState, useRef, useEffect } from "react";
import { Plus, X, Tag } from "lucide-react";
import { useTags, useCreateTag, useAddPaperToTag } from "@/hooks/useTags";

interface TagPickerProps {
  paperId: string;
  onClose: () => void;
}

export default function TagPicker({ paperId, onClose }: TagPickerProps) {
  const { data: tags } = useTags();
  const createTag = useCreateTag();
  const addPaper = useAddPaperToTag();
  const [newTag, setNewTag] = useState("");
  const [filter, setFilter] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const newTagInputRef = useRef<HTMLInputElement>(null);

  const hasTags = (tags ?? []).length > 0;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  useEffect(() => {
    if (!hasTags && newTagInputRef.current) {
      newTagInputRef.current.focus();
    }
  }, [hasTags]);

  const filtered = (tags ?? []).filter((t) =>
    t.name.toLowerCase().includes(filter.toLowerCase()),
  );

  const handleAdd = (tagId: number) => {
    addPaper.mutate({ tagId, paperId });
  };

  const handleCreate = () => {
    if (!newTag.trim()) return;
    createTag.mutate(newTag.trim(), {
      onSuccess: (data) => {
        addPaper.mutate({ tagId: data.id, paperId });
        setNewTag("");
      },
    });
  };

  return (
    <div
      ref={ref}
      className="absolute top-full left-0 z-50 mt-1 w-64 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xl p-3"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Add to tag</span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
          <X size={16} />
        </button>
      </div>

      {/* Create new tag section - prominent at top */}
      <div className="mb-3 p-2 bg-brand-50 dark:bg-brand-950/50 rounded-lg border border-brand-200 dark:border-brand-800">
        <label className="block text-xs font-medium text-brand-700 dark:text-brand-400 mb-1.5">
          Create new tag
        </label>
        <div className="flex gap-2">
          <input
            ref={newTagInputRef}
            type="text"
            placeholder="Type name & press Enter"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-brand-300 dark:border-brand-700 bg-white dark:bg-gray-800 outline-none focus:ring-2 focus:ring-brand-500"
            autoFocus={!hasTags}
          />
          <button
            onClick={handleCreate}
            disabled={!newTag.trim()}
            className="px-3 py-2 rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* Existing tags section */}
      {hasTags ? (
        <>
          <div className="mb-2">
            <input
              type="text"
              placeholder="Search existing tags..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {filtered.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-2">
                No tags match "{filter}"
              </p>
            ) : (
              filtered.map((tag) => (
                <button
                  key={tag.id}
                  onClick={() => handleAdd(tag.id)}
                  className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex items-center gap-2"
                >
                  <Tag size={14} className="text-gray-400" />
                  <span className="flex-1">{tag.name}</span>
                  <span className="text-xs text-gray-400">({tag.paper_count})</span>
                </button>
              ))
            )}
          </div>
        </>
      ) : (
        <div className="text-center py-3">
          <Tag size={24} className="mx-auto text-gray-300 dark:text-gray-600 mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">No tags yet</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Create your first tag above
          </p>
        </div>
      )}
    </div>
  );
}
