import { useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  Home,
  Search,
  Tags,
  FolderOpen,
  Bookmark,
  Settings,
  Moon,
  Sun,
  Menu,
  X,
  LogIn,
  ChevronDown,
  LogOut,
  Github,
  Compass,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { useLogout } from "@/hooks/useAuth";
import SearchBar from "@/components/search/SearchBar";

const NAV_ITEMS = [
  { to: "/", icon: Home, label: "Home" },
  { to: "/tags", icon: Tags, label: "Tags" },
  { to: "/collections", icon: FolderOpen, label: "Collections" },
  { to: "/collections/explore", icon: Compass, label: "Explore" },
  { to: "/saved", icon: Bookmark, label: "Saved" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { darkMode, toggleDarkMode, sidebarOpen, toggleSidebar } = useUIStore();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const logout = useLogout();

  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      {/* Mobile header */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <Link to="/" className="text-lg font-bold text-brand-700 dark:text-brand-400">
          arxiv radar
        </Link>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              useUIStore.getState().openSidebar();
              useUIStore.getState().requestSearchFocus();
            }}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Search"
          >
            <Search size={18} />
          </button>
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label={sidebarOpen ? "Close menu" : "Open menu"}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </header>

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0 fixed md:sticky top-0 left-0 z-40 w-64 h-[100dvh] bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-transform duration-200 flex flex-col overflow-y-auto`}
      >
        <div className="hidden md:flex items-center px-6 py-5">
          <Link to="/" className="text-xl font-bold text-brand-700 dark:text-brand-400">
            arxiv radar
          </Link>
        </div>

        <div className="px-3 pt-4 md:pt-0 pb-2">
          <SearchBar />
        </div>

        <nav className="md:flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                onClick={() => useUIStore.getState().closeSidebar()}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-400"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="md:mt-auto px-3 py-4 border-t border-gray-200 dark:border-gray-800 space-y-2">
          <button
            onClick={toggleDarkMode}
            className="hidden md:flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            {darkMode ? "Light mode" : "Dark mode"}
          </button>
          {!user && (
            <Link
              to="/login"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <LogIn size={18} />
              Sign in
            </Link>
          )}
          {user && (
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-3 px-3 py-2.5 w-full text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                <div className="w-7 h-7 rounded-full bg-brand-200 dark:bg-brand-800 flex items-center justify-center text-xs font-bold text-brand-800 dark:text-brand-200">
                  {user.email[0].toUpperCase()}
                </div>
                <span className="flex-1 text-left truncate">{user.email.split("@")[0]}</span>
                <ChevronDown size={14} className={`transition-transform ${userMenuOpen ? "rotate-180" : ""}`} />
              </button>
              {userMenuOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
                  <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Signed in as</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{user.email}</p>
                  </div>
                  <Link
                    to="/settings"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Settings size={16} />
                    Settings
                  </Link>
                  <button
                    onClick={() => {
                      logout.mutate();
                      setUserMenuOpen(false);
                    }}
                    className="flex items-center gap-2 px-3 py-2 w-full text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                  >
                    <LogOut size={16} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="flex items-center gap-3 px-3 pt-3 text-xs text-gray-400 dark:text-gray-500">
            <a
              href="https://github.com/deepweather/arxiv-radar"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <Github size={13} />
              GitHub
            </a>
            <Link
              to="/imprint"
              onClick={() => useUIStore.getState().closeSidebar()}
              className="hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              Imprint
            </Link>
          </div>
        </div>
      </aside>

      {/* Backdrop for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={toggleSidebar}
        />
      )}

      {/* Main content */}
      <main className="flex-1 min-h-screen flex flex-col">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
          <Outlet />
        </div>
        <footer className="border-t border-gray-200 dark:border-gray-800 py-6 mb-16 md:mb-0">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-gray-400 dark:text-gray-600">
            <span className="font-medium">arxiv radar</span>
            <a
              href="https://github.com/deepweather/arxiv-radar"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-gray-600 dark:hover:text-gray-400 transition-colors"
            >
              <Github size={12} />
              GitHub
            </a>
            <Link to="/imprint" className="hover:text-gray-600 dark:hover:text-gray-400 transition-colors">
              Imprint
            </Link>
            <span>&copy; {new Date().getFullYear()}</span>
          </div>
        </footer>
      </main>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 flex justify-around py-2">
        {NAV_ITEMS.slice(0, 4).map(({ to, icon: Icon, label }) => {
          const active = pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className={`flex flex-col items-center gap-0.5 text-xs ${
                active
                  ? "text-brand-600 dark:text-brand-400"
                  : "text-gray-500 dark:text-gray-500"
              }`}
            >
              <Icon size={20} />
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
