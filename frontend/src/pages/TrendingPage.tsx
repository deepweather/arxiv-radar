import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import PaperList from "@/components/papers/PaperList";
import { Paper } from "@/types";

export default function TrendingPage() {
  const [days, setDays] = useState(7);
  const { data, isLoading } = useQuery<{ papers: Paper[] }>({
    queryKey: ["trending", days],
    queryFn: async () => {
      const { data } = await api.get(`/social/trending?days=${days}&limit=50`);
      return data;
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Trending</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Papers most tagged by the community
        </p>
      </div>

      <div className="flex gap-2">
        {[3, 7, 14, 30].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            aria-pressed={days === d}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              days === d
                ? "border-brand-400 bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                : "border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            {d} days
          </button>
        ))}
      </div>

      <PaperList papers={data?.papers ?? []} loading={isLoading} />
    </div>
  );
}
