import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import api from "@/api/client";
import { Paper } from "@/types";

interface PapersResponse {
  papers: Paper[];
  page_size: number;
}

export function usePapers(params?: {
  q?: string;
  days?: number;
  categories?: string;
  limit?: number;
  sort?: string;
  excludeTagged?: boolean;
}) {
  const limit = params?.limit ?? 25;
  return useInfiniteQuery<PapersResponse>({
    queryKey: ["papers", params],
    queryFn: async ({ pageParam = 0 }) => {
      const searchParams = new URLSearchParams();
      if (params?.q) searchParams.set("q", params.q);
      if (params?.days) searchParams.set("days", String(params.days));
      if (params?.categories) searchParams.set("categories", params.categories);
      if (params?.sort) searchParams.set("sort", params.sort);
      if (params?.excludeTagged) searchParams.set("exclude_tagged", "true");
      searchParams.set("limit", String(limit));
      searchParams.set("offset", String(pageParam));
      const { data } = await api.get(`/papers?${searchParams}`);
      return data;
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      if (lastPage.papers.length < limit) return undefined;
      return allPages.reduce((acc, page) => acc + page.papers.length, 0);
    },
  });
}

export function usePaper(id: string) {
  return useQuery<Paper>({
    queryKey: ["paper", id],
    queryFn: async () => {
      const { data } = await api.get(`/papers/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useSimilarPapers(id: string) {
  return useQuery<{ papers: Paper[] }>({
    queryKey: ["paper", id, "similar"],
    queryFn: async () => {
      const { data } = await api.get(`/papers/${id}/similar`);
      return data;
    },
    enabled: !!id,
  });
}

export function useRecommendations(type: "for-you" | "tag", tagId?: number) {
  const url = type === "for-you" ? "/recommendations/for-you" : `/recommendations/tag/${tagId}`;
  return useQuery<{ papers: Paper[] }>({
    queryKey: ["recommendations", type, tagId],
    queryFn: async () => {
      const { data } = await api.get(url);
      return data;
    },
    enabled: type === "for-you" || !!tagId,
  });
}
