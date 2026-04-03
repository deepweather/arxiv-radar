import { useState, useRef, useEffect } from "react";
import { Plus, X } from "lucide-react";
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

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

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
      className="absolute top-full left-0 z-50 mt-1 w-56 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-xl p-2"
    >
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs font-medium text-gray-500">Add to tag</span>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X size={14} />
        </button>
      </div>
      <input
        type="text"
        placeholder="Filter tags..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-1 focus:ring-brand-500 mb-1"
        autoFocus
      />
      <div className="max-h-40 overflow-y-auto space-y-0.5">
        {filtered.map((tag) => (
          <button
            key={tag.id}
            onClick={() => handleAdd(tag.id)}
            className="w-full text-left px-2 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            {tag.name}
            <span className="ml-1 text-xs text-gray-400">({tag.paper_count})</span>
          </button>
        ))}
      </div>
      <div className="mt-1 flex gap-1">
        <input
          type="text"
          placeholder="New tag..."
          value={newTag}
          onChange={(e) => setNewTag(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          className="flex-1 px-2 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none"
        />
        <button
          onClick={handleCreate}
          className="p-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}
