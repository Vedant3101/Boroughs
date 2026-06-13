import { api, ACCESS_KEY, REFRESH_KEY } from "./client";

export interface User {
  id: number;
  username: string;
  email: string;
  date_joined: string;
}

export interface AuthResponse {
  user: User;
  access: string;
  refresh: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export async function register(payload: {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/auth/register/", payload);
  storeTokens({ access: data.access, refresh: data.refresh });
  return data;
}

export async function login(
  username: string,
  password: string,
): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/auth/login/", {
    username,
    password,
  });
  storeTokens(data);
  return data;
}

export async function me(): Promise<User> {
  const { data } = await api.get<User>("/auth/me/");
  return data;
}

export function logout(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access);
  localStorage.setItem(REFRESH_KEY, tokens.refresh);
}
