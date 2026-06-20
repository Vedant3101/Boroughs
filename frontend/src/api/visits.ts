import { api } from "./client";

export interface Visit {
  id: number;
  bar: number;
  bar_name: string;
  visited_at: string;
  notes: string;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function fetchVisits(
  page_size = 100,
): Promise<Paginated<Visit>> {
  const { data } = await api.get<Paginated<Visit>>("/visits/", {
    params: { page_size },
  });
  return data;
}

export async function createVisit(payload: {
  bar: number;
  visited_at: string;
  notes?: string;
}): Promise<Visit> {
  const { data } = await api.post<Visit>("/visits/", payload);
  return data;
}

export async function deleteVisit(id: number): Promise<void> {
  await api.delete(`/visits/${id}/`);
}
