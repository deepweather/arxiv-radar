export interface SimilarPaper {
  id: string;
  title: string;
  similarity: number;
}

export interface UserTag {
  id: number;
  name: string;
}

export interface Paper {
  id: string;
  title: string;
  summary: string;
  authors: { name: string }[];
  categories: string[];
  pdf_url: string | null;
  published_at: string;
  updated_at: string;
  score?: number;
  similarity?: number;
  similar_to?: SimilarPaper[];
  user_tags?: UserTag[];
}

export interface Tag {
  id: number;
  name: string;
  paper_count?: number;
}

export interface Collection {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  share_slug?: string;
  paper_count?: number;
  view_count?: number;
  owner_name?: string;
  is_owner?: boolean;
  created_at: string;
}
