import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { unwrap } from "@/api/errors";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => unwrap(await api.GET("/api/v1/me")),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useTelegramAuth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (initData: string) =>
      unwrap(await api.POST("/api/v1/auth/telegram", { body: { init_data: initData } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLinkAuth() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (token: string) =>
      unwrap(await api.POST("/api/v1/auth/link", { body: { token } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/v1/auth/logout")),
    onSuccess: () => {
      queryClient.clear();
    },
  });
}