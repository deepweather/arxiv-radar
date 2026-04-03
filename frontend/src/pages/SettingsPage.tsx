import { useState } from "react";
import { Link } from "react-router-dom";
import { Moon, Sun, Bell, Trash2, Plus, LogOut } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { useLogout } from "@/hooks/useAuth";
import { useTags } from "@/hooks/useTags";

interface Webhook {
  id: number;
  platform: string;
  webhook_url: string;
  tag_id: number | null;
  enabled: boolean;
}

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const { darkMode, toggleDarkMode } = useUIStore();
  const logout = useLogout();
  const { data: tags } = useTags();
  const qc = useQueryClient();

  const [platform, setPlatform] = useState("slack");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookTagId, setWebhookTagId] = useState<string>("");

  const { data: webhooks } = useQuery<Webhook[]>({
    queryKey: ["webhooks"],
    queryFn: async () => {
      const { data } = await api.get("/webhooks");
      return data;
    },
    enabled: !!user,
  });

  const createWebhook = useMutation({
    mutationFn: async () => {
      await api.post("/webhooks", {
        platform,
        webhook_url: webhookUrl,
        tag_id: webhookTagId ? parseInt(webhookTagId) : null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["webhooks"] });
      setWebhookUrl("");
    },
  });

  const deleteWebhook = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/webhooks/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });

  if (!user) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold mb-2">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">
          <Link to="/login" className="text-brand-600 hover:underline">Sign in</Link> to manage settings
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold mb-1">Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Profile, preferences, and notification configuration
        </p>
      </div>

      {/* Profile */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Profile</h2>
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 space-y-2">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-brand-200 dark:bg-brand-800 flex items-center justify-center text-sm font-bold text-brand-800 dark:text-brand-200">
              {user.email[0].toUpperCase()}
            </div>
            <div>
              <p className="font-medium">{user.email}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Appearance */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Appearance</h2>
        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {darkMode ? <Moon size={18} /> : <Sun size={18} />}
              <span>Dark mode</span>
            </div>
            <button
              onClick={toggleDarkMode}
              role="switch"
              aria-checked={darkMode}
              aria-label="Toggle dark mode"
              className={`relative w-11 h-6 rounded-full transition-colors ${
                darkMode ? "bg-brand-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                  darkMode ? "translate-x-5" : ""
                }`}
              />
            </button>
          </div>
        </div>
      </section>

      {/* Webhooks */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Bell size={18} />
          Notification Webhooks
        </h2>

        {(webhooks ?? []).map((wh) => (
          <div
            key={wh.id}
            className="flex items-center justify-between p-3 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-sm"
          >
            <div>
              <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-800 mr-2">
                {wh.platform}
              </span>
              <span className="text-gray-500 break-all">{wh.webhook_url.slice(0, 50)}...</span>
            </div>
            <button
              onClick={() => deleteWebhook.mutate(wh.id)}
              className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}

        <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 space-y-3">
          <div className="flex gap-2">
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm"
            >
              <option value="slack">Slack</option>
              <option value="discord">Discord</option>
            </select>
            <select
              value={webhookTagId}
              onChange={(e) => setWebhookTagId(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm"
            >
              <option value="">All tags</option>
              {(tags ?? []).map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <input
            type="url"
            placeholder="Webhook URL"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 outline-none focus:ring-2 focus:ring-brand-500 text-sm"
          />
          <button
            onClick={() => createWebhook.mutate()}
            disabled={!webhookUrl || createWebhook.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            <Plus size={14} />
            Add webhook
          </button>
        </div>
      </section>

      {/* Logout */}
      <section>
        <button
          onClick={() => logout.mutate()}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </section>
    </div>
  );
}
