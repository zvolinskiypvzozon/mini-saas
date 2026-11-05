export type Role = "owner" | "admin" | "member";
export type TaskStatus = "todo" | "in_progress" | "done";

export interface User {
  id: string;
  email: string;
  role: Role;
  organization_id: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  assignee_id: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoredFile {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  created_at: string;
}
