import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";

import { api, errorText } from "../api";
import { useAuth } from "../auth";
import { Alert, Button, Card, Field, Input } from "../ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [organization, setOrganization] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const isRegister = mode === "register";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isRegister) await api.register(organization, email, password);
      await login(email, password);
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <Card>
        <h1>{isRegister ? "Новая организация" : "Вход"}</h1>
        <form className="stack" onSubmit={submit}>
          {isRegister && (
            <Field label="Название организации">
              <Input
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                minLength={2}
                required
              />
            </Field>
          )}
          <Field label="Email">
            <Input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </Field>
          <Field label="Пароль">
            <Input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={isRegister ? 8 : undefined}
              required
            />
          </Field>
          <Alert>{error}</Alert>
          <Button type="submit" disabled={busy}>
            {isRegister ? "Зарегистрироваться" : "Войти"}
          </Button>
        </form>
        <Button
          variant="secondary"
          onClick={() => {
            setMode(isRegister ? "login" : "register");
            setError("");
          }}
        >
          {isRegister ? "У меня уже есть аккаунт" : "Создать организацию"}
        </Button>
      </Card>
    </div>
  );
}
