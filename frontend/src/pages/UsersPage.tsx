import { useCallback, useEffect, useState, type FormEvent } from "react";

import { api, errorText } from "../api";
import type { User } from "../types";
import { Alert, Badge, Button, Card, Field, Input, Select } from "../ui";

export function UsersPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"member" | "admin">("member");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.users().then(setUsers).catch((err) => setError(errorText(err)));
  }, []);

  useEffect(load, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.createUser(email, password, role);
      setEmail("");
      setPassword("");
      setRole("member");
      load();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Сотрудники</h1>
      </div>

      <Card>
        <h2>Добавить сотрудника</h2>
        <form className="row" onSubmit={create}>
          <Field label="Email">
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Пароль">
            <Input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </Field>
          <Field label="Роль">
            <Select value={role} onChange={(e) => setRole(e.target.value as "member" | "admin")}>
              <option value="member">member</option>
              <option value="admin">admin</option>
            </Select>
          </Field>
          <Button type="submit">Добавить</Button>
        </form>
      </Card>

      <Alert>{error}</Alert>

      <Card>
        {users === null ? (
          <p className="muted">Загрузка…</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Роль</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>
                      <Badge tone={user.role === "member" ? "neutral" : "warning"}>{user.role}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
