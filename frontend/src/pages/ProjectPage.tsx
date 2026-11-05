import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, errorText } from "../api";
import { useAuth } from "../auth";
import type { Project, Task, TaskStatus, User } from "../types";
import { Alert, Button, Card, Field, Input, Select, STATUS_LABELS, StatusBadge } from "../ui";

const STATUSES: TaskStatus[] = ["todo", "in_progress", "done"];

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [orgUsers, setOrgUsers] = useState<User[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, t, m] = await Promise.all([
        api.project(projectId),
        api.tasks(projectId),
        api.members(projectId),
      ]);
      setProject(p);
      setTasks(t);
      setMembers(m);
      if (isAdmin) setOrgUsers(await api.users());
    } catch (err) {
      setError(errorText(err));
    }
  }, [projectId, isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    setError("");
    try {
      await action();
      await load();
      return true;
    } catch (err) {
      setError(errorText(err));
      return false;
    }
  }

  async function deleteProject() {
    if (!project || !window.confirm(`Удалить проект «${project.name}» со всеми задачами?`)) return;
    try {
      await api.deleteProject(project.id);
      navigate("/");
    } catch (err) {
      setError(errorText(err));
    }
  }

  if (!project) {
    return error ? <Alert>{error}</Alert> : <p className="muted">Загрузка…</p>;
  }

  const emailById = new Map(members.map((m) => [m.id, m.email]));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{project.name}</h1>
          {project.description && <p className="muted">{project.description}</p>}
        </div>
        {isAdmin && (
          <Button variant="danger" onClick={deleteProject}>
            Удалить проект
          </Button>
        )}
      </div>

      <Alert>{error}</Alert>

      <NewTaskForm
        members={members}
        onCreate={(data) => run(() => api.createTask(project.id, data))}
      />

      <div className="board">
        {STATUSES.map((status) => {
          const column = tasks.filter((t) => t.status === status);
          return (
            <section key={status} className="board__column" aria-label={STATUS_LABELS[status]}>
              <h2>
                {STATUS_LABELS[status]} <span className="muted">{column.length}</span>
              </h2>
              {column.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  members={members}
                  assigneeEmail={task.assignee_id ? emailById.get(task.assignee_id) : undefined}
                  onChange={(patch) => run(() => api.updateTask(task.id, patch))}
                  onDelete={() => run(() => api.deleteTask(task.id))}
                />
              ))}
            </section>
          );
        })}
      </div>

      <Members
        members={members}
        orgUsers={orgUsers}
        isAdmin={isAdmin}
        onAdd={(userId) => run(() => api.addMember(project.id, userId))}
        onRemove={(userId) => run(() => api.removeMember(project.id, userId))}
      />
    </>
  );
}

interface NewTaskFormProps {
  members: User[];
  onCreate: (data: { title: string; assignee_id: string | null; due_date: string | null }) => Promise<boolean>;
}

function NewTaskForm({ members, onCreate }: NewTaskFormProps) {
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");
  const [dueDate, setDueDate] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const created = await onCreate({ title, assignee_id: assignee || null, due_date: dueDate || null });
    if (!created) return;
    setTitle("");
    setAssignee("");
    setDueDate("");
  }

  return (
    <Card>
      <h2>Новая задача</h2>
      <form className="row" onSubmit={submit}>
        <Field label="Название">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </Field>
        <Field label="Исполнитель">
          <Select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">— не назначен —</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.email}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Срок">
          <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </Field>
        <Button type="submit">Добавить</Button>
      </form>
    </Card>
  );
}

interface TaskCardProps {
  task: Task;
  members: User[];
  assigneeEmail?: string;
  onChange: (patch: { status?: TaskStatus; assignee_id?: string | null }) => void;
  onDelete: () => void;
}

function TaskCard({ task, members, assigneeEmail, onChange, onDelete }: TaskCardProps) {
  const overdue = task.due_date !== null && task.status !== "done" && task.due_date < today();
  return (
    <Card>
      <strong>{task.title}</strong>
      <div className="task__meta">
        <StatusBadge status={task.status} />
        {assigneeEmail && <span>{assigneeEmail}</span>}
        {task.due_date && (
          <span style={overdue ? { color: "var(--color-danger)" } : undefined}>
            до {task.due_date}
          </span>
        )}
      </div>
      <Select
        aria-label="Статус"
        value={task.status}
        onChange={(e) => onChange({ status: e.target.value as TaskStatus })}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {STATUS_LABELS[s]}
          </option>
        ))}
      </Select>
      <Select
        aria-label="Исполнитель"
        value={task.assignee_id ?? ""}
        onChange={(e) => onChange({ assignee_id: e.target.value || null })}
      >
        <option value="">— не назначен —</option>
        {members.map((m) => (
          <option key={m.id} value={m.id}>
            {m.email}
          </option>
        ))}
      </Select>
      <Button variant="danger" size="sm" onClick={onDelete}>
        Удалить
      </Button>
    </Card>
  );
}

interface MembersProps {
  members: User[];
  orgUsers: User[];
  isAdmin: boolean;
  onAdd: (userId: string) => void;
  onRemove: (userId: string) => void;
}

function Members({ members, orgUsers, isAdmin, onAdd, onRemove }: MembersProps) {
  const [selected, setSelected] = useState("");
  const memberIds = new Set(members.map((m) => m.id));
  const candidates = orgUsers.filter((u) => !memberIds.has(u.id));

  return (
    <Card>
      <h2>Участники</h2>
      <ul className="stack" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
        {members.map((m) => (
          <li key={m.id} className="row" style={{ alignItems: "center" }}>
            <span>{m.email}</span>
            <span className="muted">{m.role}</span>
            {isAdmin && (
              <Button variant="danger" size="sm" onClick={() => onRemove(m.id)}>
                Убрать
              </Button>
            )}
          </li>
        ))}
      </ul>
      {isAdmin && candidates.length > 0 && (
        <div className="row">
          <Field label="Добавить сотрудника">
            <Select value={selected} onChange={(e) => setSelected(e.target.value)}>
              <option value="">— выберите —</option>
              {candidates.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email}
                </option>
              ))}
            </Select>
          </Field>
          <Button
            disabled={!selected}
            onClick={() => {
              onAdd(selected);
              setSelected("");
            }}
          >
            Добавить
          </Button>
        </div>
      )}
    </Card>
  );
}

function today(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}
