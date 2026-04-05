import { create } from "zustand";

interface UIState {
  darkMode: boolean;
  sidebarOpen: boolean;
  searchFocusRequested: boolean;
  toggleDarkMode: () => void;
  toggleSidebar: () => void;
  openSidebar: () => void;
  closeSidebar: () => void;
  requestSearchFocus: () => void;
  clearSearchFocus: () => void;
}

const prefersDark =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-color-scheme: dark)").matches;

export const useUIStore = create<UIState>((set) => ({
  darkMode: prefersDark,
  sidebarOpen: false,
  searchFocusRequested: false,
  toggleDarkMode: () =>
    set((s) => {
      const next = !s.darkMode;
      document.documentElement.classList.toggle("dark", next);
      return { darkMode: next };
    }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  openSidebar: () => set({ sidebarOpen: true }),
  closeSidebar: () => set({ sidebarOpen: false }),
  requestSearchFocus: () => set({ searchFocusRequested: true }),
  clearSearchFocus: () => set({ searchFocusRequested: false }),
}));
