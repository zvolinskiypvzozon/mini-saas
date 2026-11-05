import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth";
import { FilesPage } from "./pages/FilesPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { UsersPage } from "./pages/UsersPage";
import { Badge, Button } from "./ui";

function Layout({ children }: { children: ReactNode }) {
  const { user, isAdmin, logout } = useAuth();
  return (
    <>
      <header className="header">
        <NavLink to="/" className="header__brand">
          Mini SaaS
        </NavLink>
        <nav className="header__nav">
          <NavLink to="/" end>
            Проекты
          </NavLink>
          <NavLink to="/files">Файлы</NavLink>
          {isAdmin && <NavLink to="/users">Сотрудники</NavLink>}
        </nav>
        <div className="header__user">
          <span>{user?.email}</span>
          <Badge>{user?.role}</Badge>
          <Button variant="secondary" size="sm" onClick={logout}>
            Выйти
          </Button>
        </div>
      </header>
      <main className="page">{children}</main>
    </>
  );
}

function Protected({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return <p className="page muted">Загрузка…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Protected><ProjectsPage /></Protected>} />
      <Route path="/projects/:projectId" element={<Protected><ProjectPage /></Protected>} />
      <Route path="/files" element={<Protected><FilesPage /></Protected>} />
      <Route path="/users" element={<Protected adminOnly><UsersPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
