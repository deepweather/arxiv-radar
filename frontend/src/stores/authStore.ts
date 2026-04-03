import { create } from "zustand";

export interface User {
  id: string;
  email: string;
  is_email_verified: boolean;
  digest_enabled: boolean;
  digest_frequency: string;
}

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));
