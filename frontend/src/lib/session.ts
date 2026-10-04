// Session cache ownership: begin/end the react-query cache alongside the server session.
import { queryClient } from "@/lib/queryClient";
import { apiPost } from "@/lib/api";

export function beginSession() {
  queryClient.clear();
}

export async function endSession() {
  try {
    await apiPost("/auth/logout");
  } finally {
    queryClient.clear();
  }
}
