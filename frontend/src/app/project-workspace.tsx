
"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createProject,
  getCurrentUser,
  getProjects,
  hasSession,
  login,
  logout,
  register,
  type Project,
  type User,
} from "@/lib/api";

export default function ProjectWorkspace() {
  const [user, setUser] = useState<User | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadProjects = useCallback(async () => {
    const result = await getProjects();
    setProjects(result);
  }, []);

  const loadSession = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      setProjects([]);
      setLoading(false);
      return;
    }

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      await loadProjects();
    } catch {
      logout();
      setUser(null);
      setProjects([]);
      setError("Your session expired. Please sign in again.");
    } finally {
      setLoading(false);
    }
  }, [loadProjects]);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);

    try {
      if (mode === "register") {
        await register({
          email: email.trim(),
          full_name: fullName.trim(),
          password,
        });

        await login(email.trim(), password);
        setMessage("Account created successfully.");
      } else {
        await login(email.trim(), password);
        setMessage("Signed in successfully.");
      }

      setPassword("");
      await loadSession();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Authentication failed."
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!projectName.trim()) {
      setError("Enter a project name.");
      return;
    }

    setSaving(true);

    try {
      await createProject({
        name: projectName.trim(),
        description: description.trim() || undefined,
      });

      setProjectName("");
      setDescription("");
      await loadProjects();
      setMessage("Project saved successfully.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create project."
      );
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    logout();
    setUser(null);
    setProjects([]);
    setEmail("");
    setPassword("");
    setError("");
    setMessage("You have signed out.");
  }

  return (
    <section className="project-workspace panel">
      <div className="panel-heading">
        <div>
          <div className="heading-with-icon">
            <span className="panel-title-icon">◈</span>
            <h2>My Projects</h2>
          </div>
          <p>Manage projects saved to your account</p>
        </div>

        {user && (
          <button
            className="subtle-button"
            type="button"
            onClick={handleLogout}
          >
            Sign out
          </button>
        )}
      </div>

      {error && (
        <p className="project-message project-error" role="alert">
          {error}
        </p>
      )}

      {message && (
        <p className="project-message" role="status">
          {message}
        </p>
      )}

      {loading ? (
        <p className="project-empty">Checking your session...</p>
      ) : user ? (
        <>
          <p className="project-welcome">
            Signed in as <strong>{user.full_name}</strong> ({user.email})
          </p>

          <form className="project-create-form" onSubmit={handleCreateProject}>
            <label className="field-label" htmlFor="new-project-name">
              Project name
            </label>
            <input
              id="new-project-name"
              required
              maxLength={150}
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              placeholder="e.g. AI Engineering Agent"
            />

            <label className="field-label" htmlFor="new-project-description">
              Description (optional)
            </label>
            <textarea
              id="new-project-description"
              rows={2}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What does this project do?"
            />

            <button
              className="primary-button"
              type="submit"
              disabled={saving}
            >
              {saving ? "Saving..." : "Create project"}
            </button>
          </form>

          <div className="project-list">
            <h3>Your saved projects ({projects.length})</h3>

            {projects.length === 0 ? (
              <p className="project-empty">
                No projects yet. Create your first project above.
              </p>
            ) : (
              projects.map((project) => (
                <article className="project-item" key={project.id}>
                  <div>
                    <strong>{project.name}</strong>
                    <p>
                      {project.description || "No description provided."}
                    </p>
                    <small>
                      Created {new Date(project.created_at).toLocaleDateString()}
                    </small>
                  </div>
                  <span className="project-status">{project.status}</span>
                </article>
              ))
            )}
          </div>
        </>
      ) : (
        <form className="project-auth-form" onSubmit={handleAuth}>
          <h3>{mode === "login" ? "Sign in to ENGINEOS" : "Create your account"}</h3>
          <p>Sign in to access projects stored in your backend database.</p>

          {mode === "register" && (
            <>
              <label className="field-label" htmlFor="auth-full-name">
                Full name
              </label>
              <input
                id="auth-full-name"
                required
                maxLength={150}
                autoComplete="name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your full name"
              />
            </>
          )}

          <label className="field-label" htmlFor="auth-email">
            Email
          </label>
          <input
            id="auth-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />

          <label className="field-label" htmlFor="auth-password">
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            required
            minLength={8}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
          />

          <button
            className="primary-button"
            type="submit"
            disabled={saving}
          >
            {saving
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>

          <p className="project-auth-switch">
            {mode === "login"
              ? "New to ENGINEOS?"
              : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
                setMessage("");
              }}
            >
              {mode === "login" ? "Create account" : "Sign in"}
            </button>
          </p>
        </form>
      )}
    </section>
  );
}
