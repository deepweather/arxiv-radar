import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/api/client";
import { useAuthStore, User } from "@/stores/authStore";

let accessToken: string | null = null;

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
}

export function useMe() {
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const { data } = await api.get("/auth/me");
      setUser(data);
      return data;
    },
    retry: false,
    enabled: !!accessToken,
  });
}

interface LoginPayload {
  email: string;
  password: string;
  company: string;
  tz_offset: number;
}

interface RegisterPayload {
  email: string;
  password: string;
  company: string;
  tz_offset: number;
}

export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: LoginPayload) => {
      const { data } = await api.post("/auth/login", body);
      return data;
    },
    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      const { data: user } = await api.get("/auth/me");
      setUser(user);
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      navigate("/");
    },
  });
}

export function useRegister() {
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (body: RegisterPayload) => {
      const { data } = await api.post("/auth/register", body);
      return data;
    },
    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      const { data: user } = await api.get("/auth/me");
      setUser(user);
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      navigate("/");
    },
  });
}

export function useLogout() {
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await api.post("/auth/logout");
    },
    onSuccess: () => {
      setAccessToken(null);
      setUser(null);
      queryClient.clear();
      navigate("/login");
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async (email: string) => {
      const { data } = await api.post("/auth/resend-verification", { email });
      return data;
    },
  });
}
