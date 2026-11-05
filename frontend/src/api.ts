import type { Project, Role, StoredFile, Task, TaskStatus, User } from "./types";

const TOKEN_KEY = "token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // хранилище недоступно (приватный режим) — просто не запоминаем вход
  }
}

let onUnauthorized: () => void = () => {};

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item: { msg: string }) => item.msg).join("; ");
    }
  } catch {
    // тело не JSON
  }
  return `Ошибка ${response.status}`;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(path, { method: options.method ?? "GET", headers, body });
  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Неизвестная ошибка";
}

export interface TaskInput {
  title: string;
  assignee_id: string | null;
  due_date: string | null;
}

export type TaskPatch = Partial<TaskInput & { status: TaskStatus; description: string | null }>;

export const api = {
  register: (organization_name: string, email: string, password: string) =>
    request<User>("/api/auth/register", {
      method: "POST",
      body: { organization_name, email, password },
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  me: () => request<User>("/api/me"),

  users: () => request<User[]>("/api/users"),
  createUser: (email: string, password: string, role: Exclude<Role, "owner">) =>
    request<User>("/api/users", { method: "POST", body: { email, password, role } }),

  projects: () => request<Project[]>("/api/projects"),
  project: (id: string) => request<Project>(`/api/projects/${id}`),
  createProject: (name: string, description: string | null) =>
    request<Project>("/api/projects", { method: "POST", body: { name, description } }),
  deleteProject: (id: string) => request<void>(`/api/projects/${id}`, { method: "DELETE" }),

  members: (projectId: string) => request<User[]>(`/api/projects/${projectId}/members`),
  addMember: (projectId: string, userId: string) =>
    request<User>(`/api/projects/${projectId}/members`, {
      method: "POST",
      body: { user_id: userId },
    }),
  removeMember: (projectId: string, userId: string) =>
    request<void>(`/api/projects/${projectId}/members/${userId}`, { method: "DELETE" }),

  tasks: (projectId: string) => request<Task[]>(`/api/projects/${projectId}/tasks`),
  createTask: (projectId: string, data: TaskInput) =>
    request<Task>(`/api/projects/${projectId}/tasks`, { method: "POST", body: data }),
  updateTask: (id: string, data: TaskPatch) =>
    request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: data }),
  deleteTask: (id: string) => request<void>(`/api/tasks/${id}`, { method: "DELETE" }),

  files: () => request<StoredFile[]>("/api/files"),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<StoredFile>("/api/files", { method: "POST", form });
  },
  downloadUrl: (id: string) =>
    request<{ url: string; expires_in: number }>(`/api/files/${id}/download`),
  deleteFile: (id: string) => request<void>(`/api/files/${id}`, { method: "DELETE" }),
};
