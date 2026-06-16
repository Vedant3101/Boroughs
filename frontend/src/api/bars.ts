import { api } from "./client";

export interface Bar {
  id: number;
  name: string;
  address: string;
  borough: string;
  borough_display: string;
  latitude: string;
  longitude: string;
  price_level: number | null;
  price_level_display: string | null;
  google_rating: string | null;
  google_rating_count: number | null;
}

export interface PaginatedBars {
  count: number;
  next: string | null;
  previous: string | null;
  results: Bar[];
}

export interface BarFilters {
  lat?: number;
  lng?: number;
  radius?: number;
  search?: string;
  price_min?: number;
  price_max?: number;
  borough?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export async function fetchBars(
  filters: BarFilters = {},
): Promise<PaginatedBars> {
  const { data } = await api.get<PaginatedBars>("/bars/", { params: filters });
  return data;
}

export async function fetchBar(id: number): Promise<Bar> {
  const { data } = await api.get<Bar>(`/bars/${id}/`);
  return data;
}
