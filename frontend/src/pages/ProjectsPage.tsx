import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { api, errorText } from "../api";
import { useAuth } from "../auth";
import type { Project } from "../types";
import { Alert, Button, Card, Field, Input } from "../ui";

export function ProjectsPage() {
  const { isAdmin } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.projects().then(setProjects).catch((err) => setError(errorText(err)));
  }, []);

  useEffect(load, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.createProject(name, description || null);
      setName("");
      setDescription("");
      load();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Проекты</h1>
      </div>

      {isAdmin && (
        <Card>
          <h2>Новый проект</h2>
          <form className="row" onSubmit={create}>
            <Field label="Название">
              <Input value={name} onChange={(e) => setName(e.target.value)} minLength={2} required />
            </Field>
            <Field label="Описание">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <Button type="submit">Создать</Button>
          </form>
        </Card>
      )}

      <Alert>{error}</Alert>

      {projects === null ? (
        <p className="muted">Загрузка…</p>
      ) : projects.length === 0 ? (
        <p className="muted">
          {isAdmin ? "Проектов пока нет. Создайте первый." : "Вас ещё не добавили ни в один проект."}
        </p>
      ) : (
        <div className="grid">
          {projects.map((project) => (
            <Link key={project.id} to={`/projects/${project.id}`} className="card card--link">
              <h2>{project.name}</h2>
              {project.description && <p className="muted">{project.description}</p>}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
