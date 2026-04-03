import { create } from "zustand";

export interface User {
  id: string;
  username: string;
  email: string;
  is_email_verified: boolean;
}

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));
