import axios from "axios";
import { useAuthStore } from "@/stores/authStore";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const { data } = await axios.post("/api/auth/refresh", {}, { withCredentials: true });
        if (data.access_token) {
          api.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
        }
        return api(original);
      } catch {
        delete api.defaults.headers.common["Authorization"];
        useAuthStore.getState().setUser(null);
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

export default api;
