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
  paper_count?: number;
  created_at: string;
}
