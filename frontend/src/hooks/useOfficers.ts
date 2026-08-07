import { useQuery } from "@tanstack/react-query";
import { api } from "../api";

export function useOfficers() {
  return useQuery({
    queryKey: ["officers"],
    queryFn: async () => {
      const res = await api.get("/public/officers");
      return res.data;
    },
  });
}
