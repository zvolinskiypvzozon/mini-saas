import { useCallback, useEffect, useRef, useState, type ChangeEvent } from "react";

import { api, errorText } from "../api";
import type { StoredFile } from "../types";
import { Alert, Button, Card } from "../ui";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

export function FilesPage() {
  const [files, setFiles] = useState<StoredFile[] | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api.files().then(setFiles).catch((err) => setError(errorText(err)));
  }, []);

  useEffect(load, [load]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      await api.uploadFile(file);
      load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function download(file: StoredFile) {
    try {
      const { url } = await api.downloadUrl(file.id);
      window.location.assign(url);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function remove(file: StoredFile) {
    if (!window.confirm(`Удалить «${file.filename}»?`)) return;
    try {
      await api.deleteFile(file.id);
      load();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Файлы</h1>
        <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
          {uploading ? "Загрузка…" : "Загрузить файл"}
        </Button>
        <input ref={inputRef} type="file" hidden onChange={upload} />
      </div>

      <Alert>{error}</Alert>

      <Card>
        {files === null ? (
          <p className="muted">Загрузка…</p>
        ) : files.length === 0 ? (
          <p className="muted">Файлов пока нет.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Имя</th>
                  <th>Размер</th>
                  <th>Загружен</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {files.map((file) => (
                  <tr key={file.id}>
                    <td>{file.filename}</td>
                    <td>{formatSize(file.size)}</td>
                    <td>{new Date(file.created_at).toLocaleString("ru-RU")}</td>
                    <td className="row" style={{ justifyContent: "flex-end" }}>
                      <Button variant="secondary" size="sm" onClick={() => download(file)}>
                        Скачать
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => remove(file)}>
                        Удалить
                      </Button>
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
