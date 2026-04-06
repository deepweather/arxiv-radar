import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import { Collection } from "@/types";
import { useAuthStore } from "@/stores/authStore";

export function useCollections() {
  const user = useAuthStore((s) => s.user);
  return useQuery<{ collections: Collection[] }>({
    queryKey: ["collections"],
    queryFn: async () => {
      const { data } = await api.get("/collections");
      return data;
    },
    enabled: !!user,
  });
}

export function useCollection(id: string) {
  return useQuery({
    queryKey: ["collections", id],
    queryFn: async () => {
      const { data } = await api.get(`/collections/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function usePublicCollections(sort: string = "trending", offset: number = 0, limit: number = 20) {
  return useQuery<{ collections: Collection[] }>({
    queryKey: ["public-collections", sort, offset, limit],
    queryFn: async () => {
      const { data } = await api.get("/collections/public", {
        params: { sort, offset, limit },
      });
      return data;
    },
  });
}

export function useCreateCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; description?: string; is_public?: boolean }) => {
      const { data } = await api.post("/collections", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });
}

export function useDeleteCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/collections/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  });
}

export function useSavePaper() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (paperId: string) => {
      await api.post("/collections/saved/papers", { paper_id: paperId });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-papers"] }),
  });
}

export function useUnsavePaper() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (paperId: string) => {
      await api.delete(`/collections/saved/papers/${paperId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-papers"] }),
  });
}

export function useSavedPapers() {
  const user = useAuthStore((s) => s.user);
  return useQuery({
    queryKey: ["saved-papers"],
    queryFn: async () => {
      const { data } = await api.get("/collections/saved/papers");
      return data;
    },
    enabled: !!user,
  });
}

export function useAddToCollection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ collectionId, paperId, note }: { collectionId: string; paperId: string; note?: string }) => {
      const { data } = await api.post(`/collections/${collectionId}/papers`, { paper_id: paperId, note: note ?? "" });
      return data;
    },
    onSuccess: (_, { collectionId }) => {
      qc.invalidateQueries({ queryKey: ["collections"] });
      qc.invalidateQueries({ queryKey: ["collections", collectionId] });
    },
  });
}
