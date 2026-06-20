import { api } from "./client";
import type { Paginated } from "./visits";

export interface Rating {
  id: number;
  bar: number;
  bar_name: string;
  score: number;
  comment: string;
  created_at: string;
  updated_at: string;
}

export async function fetchRatings(
  page_size = 100,
): Promise<Paginated<Rating>> {
  const { data } = await api.get<Paginated<Rating>>("/ratings/", {
    params: { page_size },
  });
  return data;
}

export async function upsertRating(payload: {
  bar: number;
  score: number;
  comment?: string;
}): Promise<Rating> {
  const { data } = await api.post<Rating>("/ratings/", payload);
  return data;
}

export async function patchRating(
  id: number,
  patch: { score?: number; comment?: string },
): Promise<Rating> {
  const { data } = await api.patch<Rating>(`/ratings/${id}/`, patch);
  return data;
}

export async function deleteRating(id: number): Promise<void> {
  await api.delete(`/ratings/${id}/`);
}
