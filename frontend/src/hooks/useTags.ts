import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import { Tag } from "@/types";

export function useTags() {
  return useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: async () => {
      const { data } = await api.get("/tags");
      return data;
    },
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await api.post("/tags", { name });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: number) => {
      await api.delete(`/tags/${tagId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useAddPaperToTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ tagId, paperId }: { tagId: number; paperId: string }) => {
      await api.post(`/tags/${tagId}/papers`, { paper_id: paperId });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useRemovePaperFromTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ tagId, paperId }: { tagId: number; paperId: string }) => {
      await api.delete(`/tags/${tagId}/papers/${paperId}`);
    },
    onSuccess: (_, { tagId }) => {
      qc.invalidateQueries({ queryKey: ["tags"] });
      qc.invalidateQueries({ queryKey: ["tag-papers", tagId] });
    },
  });
}

export function useTagPapers(tagId: number | null) {
  return useQuery({
    queryKey: ["tag-papers", tagId],
    queryFn: async () => {
      const { data } = await api.get(`/tags/${tagId}/papers`);
      return data;
    },
    enabled: tagId !== null,
  });
}
