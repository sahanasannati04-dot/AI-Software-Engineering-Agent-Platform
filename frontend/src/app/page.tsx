"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import ProjectWorkspace from "./project-workspace";

type RunStatus = "Completed" | "Running" | "Needs review" | "Queued";
type BackendStatus = "checking" | "connected" | "offline";

type AgentRun = {
  id: number;
  title: string;
  repository: string;
  type: string;
  status: RunStatus;
  time: string;
};

type HealthResponse = {
  status?: string;
  service?: string;
};

const navigation = [
  {
    heading: "WORKSPACE",
    items: [
      { name: "Overview", icon: "▦" },
      { name: "Repositories", icon: "⌘" },
      { name: "Agent runs", icon: "◈" },
      { name: "Change review", icon: "⇄" },
    ],
  },
  {
    heading: "ENGINEERING",
    items: [
      { name: "Code intelligence", icon: "⌕" },
      { name: "Test reports", icon: "✓" },
      { name: "Knowledge base", icon: "▤" },
    ],
  },
];

const initialRuns: AgentRun[] = [
  {
    id: 1,
    title: "Investigate authentication flow",
    repository: "agent-platform-api",
    type: "Bug investigation",
    status: "Completed",
    time: "12 min ago",
  },
  {
    id: 2,
    title: "Review repository indexing",
    repository: "repository-intelligence",
    type: "Code review",
    status: "Needs review",
    time: "28 min ago",
  },
  {
    id: 3,
    title: "Generate regression tests",
    repository: "checkout-service",
    type: "Test generation",
    status: "Running",
    time: "Started 2 min ago",
  },
];

const metrics = [
  {
    label: "Repositories indexed",
    value: "08",
    change: "+2 this week",
    icon: "⌘",
  },
  {
    label: "Agent runs",
    value: "124",
    change: "+18 this week",
    icon: "◈",
  },
  {
    label: "Tests passing",
    value: "94.2%",
    change: "+3.1% this week",
    icon: "✓",
  },
  {
    label: "Avg. investigation",
    value: "3m 18s",
    change: "Demo estimate",
    icon: "◷",
  },
];

function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`status status-${status.toLowerCase().replaceAll(" ", "-")}`}
    >
      <span className="status-dot" />
      {status}
    </span>
  );
}

export default function Home() {
  const [activeNav, setActiveNav] = useState("Overview");
  const [search, setSearch] = useState("");
  const [runs, setRuns] = useState<AgentRun[]>(initialRuns);
  const [showTask, setShowTask] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [repository, setRepository] = useState("");
  const [taskType, setTaskType] = useState("Investigate a bug");
  const [notice, setNotice] = useState("");

  // Real FastAPI health status.
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>("checking");

  const [backendService, setBackendService] = useState(
    "Checking backend health..."
  );

  useEffect(() => {
    let active = true;

    async function checkBackend() {
      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/v1/health",
          {
            cache: "no-store",
          }
        );

        if (!response.ok) {
          throw new Error(`Health check returned ${response.status}`);
        }

        const data: HealthResponse = await response.json();

        if (!active) return;

        if (data.status === "healthy") {
          setBackendStatus("connected");
          setBackendService(data.service ?? "FastAPI backend");
        } else {
          setBackendStatus("offline");
          setBackendService("Backend health check did not report healthy");
        }
      } catch {
        if (!active) return;

        setBackendStatus("offline");
        setBackendService("Cannot reach FastAPI at 127.0.0.1:8000");
      }
    }

    void checkBackend();

    const intervalId = window.setInterval(() => {
      void checkBackend();
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const filteredRuns = useMemo(() => {
    const term = search.trim().toLowerCase();

    if (!term) return runs;

    return runs.filter((run) =>
      `${run.title} ${run.repository} ${run.type} ${run.status}`
        .toLowerCase()
        .includes(term)
    );
  }, [runs, search]);

  function createTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const title = taskTitle.trim();

    if (!title) return;

    const newRun: AgentRun = {
      id: Date.now(),
      title,
      repository: repository.trim() || "Repository not selected",
      type: taskType,
      status: "Queued",
      time: "Just now",
    };

    setRuns((previous) => [newRun, ...previous]);
    setShowTask(false);
    setTaskTitle("");
    setRepository("");
    setTaskType("Investigate a bug");

    setNotice(
      "Task added to the local preview. Backend agent execution is not connected yet."
    );
    setActiveNav("Agent runs");
  }

  function selectNavigation(name: string) {
    setActiveNav(name);

    if (name !== "Overview") {
      setNotice(
        `${name} selected. Its dedicated view is part of the upcoming build.`
      );
    } else {
      setNotice("");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            selectNavigation("Overview");
          }}
        >
          <span className="brand-mark">
            <span />
            <span />
            <span />
            <span />
          </span>

          <span className="brand-copy">
            <strong>
              ENGINE<span>OS</span>
            </strong>
            <small>AI ENGINEERING PLATFORM</small>
          </span>
        </a>

        <button
          className="workspace-switcher"
          onClick={() =>
            setNotice("Workspace selector will be connected to the backend.")
          }
        >
          <span className="workspace-avatar">S</span>

          <span className="workspace-name">
            <strong>Personal workspace</strong>
            <small>Developer plan</small>
          </span>

          <span className="chevron">⌄</span>
        </button>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map((group) => (
            <div className="nav-group" key={group.heading}>
              <p className="nav-heading">{group.heading}</p>

              {group.items.map((item) => (
                <button
                  key={item.name}
                  className={`nav-item ${
                    activeNav === item.name ? "nav-item-active" : ""
                  }`}
                  onClick={() => selectNavigation(item.name)}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.name}</span>

                  {item.name === "Agent runs" && (
                    <span className="nav-count">
                      {runs.length.toString().padStart(2, "0")}
                    </span>
                  )}

                  {item.name === "Change review" && (
                    <span className="nav-indicator" />
                  )}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="usage-card">
            <div className="usage-title">
              <span>Workspace usage</span>
              <span className="usage-icon">↗</span>
            </div>

            <div className="usage-bar">
              <span />
            </div>

            <p>Preview environment</p>
            <small>Live usage appears after backend integration.</small>
          </div>

          <button
            className="nav-item settings-link"
            onClick={() => selectNavigation("Settings")}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>

          <div className="profile-row">
            <div className="profile-avatar">SS</div>

            <div className="profile-copy">
              <strong>Developer</strong>
              <small>Local environment</small>
            </div>

            <span className="profile-menu">···</span>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{activeNav}</strong>
          </div>

          <div className="topbar-actions">
            <label className="search-box">
              <span>⌕</span>

              <input
                aria-label="Search agent runs"
                placeholder="Search runs..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />

              <kbd>⌘ K</kbd>
            </label>

            <button
              className="icon-button"
              aria-label="Notifications"
              onClick={() =>
                setNotice("No live notifications are connected yet.")
              }
            >
              ♧
              <span className="notification-dot" />
            </button>

            <div className="topbar-avatar">SS</div>
          </div>
        </header>

        <div className="dashboard-content">
          <div className="preview-banner">
            <span className="preview-pulse" />
            <strong>LOCAL PREVIEW</strong>
            <span>
              Demo metrics and activity are displayed. Backend health is live.
            </span>
          </div>

          {notice && (
            <div className="notice-banner" role="status">
              <span>{notice}</span>

              <button
                aria-label="Dismiss notice"
                onClick={() => setNotice("")}
              >
                ×
              </button>
            </div>
          )}

          {/* Connected authentication and database-backed projects */}
          <ProjectWorkspace />

          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />
                DEVELOPER WORKSPACE
              </div>

              <h1>
                {activeNav === "Overview"
                  ? "Engineering overview"
                  : activeNav}
              </h1>

              <p>
                Your control center for understanding, debugging, and
                improving code.
              </p>
            </div>

            <button
              className="primary-button"
              onClick={() => setShowTask(true)}
            >
              <span className="plus-icon">＋</span>
              New task
            </button>
          </section>

          <section className="hero-panel">
            <div className="hero-grid" />
            <div className="hero-orb hero-orb-one" />
            <div className="hero-orb hero-orb-two" />

            <div className="hero-content">
              <span className="hero-kicker">
                <span className="sparkle">✳</span>
                YOUR AI ENGINEERING COPILOT
              </span>

              <h2>
                From codebase to <span>clarity.</span>
              </h2>

              <p>
                Investigate bugs, understand unfamiliar repositories, and
                plan safer code changes with an AI-assisted engineering
                workflow.
              </p>

              <div className="hero-actions">
                <button
                  className="hero-button"
                  onClick={() => setShowTask(true)}
                >
                  Start an investigation <span>↗</span>
                </button>

                <button
                  className="hero-text-button"
                  onClick={() => selectNavigation("Repositories")}
                >
                  Explore repositories <span>→</span>
                </button>
              </div>
            </div>

            <div className="hero-visual" aria-hidden="true">
              <div className="visual-ring ring-outer" />
              <div className="visual-ring ring-inner" />

              <div className="visual-core">
                <div className="core-symbol">✳</div>
              </div>

              <div className="orbit-node node-top">
                <span>⌘</span>
              </div>

              <div className="orbit-node node-right">
                <span>✓</span>
              </div>

              <div className="orbit-node node-bottom">
                <span>⌕</span>
              </div>

              <div className="orbit-node node-left">
                <span>◈</span>
              </div>

              <div className="visual-label visual-label-top">REASON</div>

              <div className="visual-label visual-label-bottom">
                EXECUTE · VALIDATE
              </div>
            </div>

            <div className="hero-footer">
              <span>
                <span className="tiny-dot cyan-dot" />
                Repository intelligence
              </span>

              <span>
                <span className="tiny-dot violet-dot" />
                Tool-assisted workflow
              </span>

              <span>
                <span className="tiny-dot green-dot" />
                Validation-first design
              </span>
            </div>
          </section>

          <div className="section-heading metrics-heading">
            <div>
              <h2>Workspace signals</h2>
              <p>Illustrative metrics for the dashboard preview</p>
            </div>

            <span className="demo-chip">DEMO METRICS</span>
          </div>

          <section
            className="metrics-grid"
            aria-label="Workspace metrics"
          >
            {metrics.map((metric, index) => (
              <article className="metric-card" key={metric.label}>
                <div className="metric-card-top">
                  <span className={`metric-icon metric-icon-${index}`}>
                    {metric.icon}
                  </span>

                  <span className="metric-menu">···</span>
                </div>

                <p className="metric-label">{metric.label}</p>

                <div className="metric-bottom">
                  <strong>{metric.value}</strong>

                  <span
                    className={`metric-change ${
                      index === 3 ? "metric-muted" : ""
                    }`}
                  >
                    {index < 3 && <span>↗</span>} {metric.change}
                  </span>
                </div>
              </article>
            ))}
          </section>

          <div className="lower-grid">
            <section className="panel activity-panel">
              <div className="panel-heading">
                <div>
                  <div className="heading-with-icon">
                    <span className="panel-title-icon">◈</span>
                    <h2>Recent agent activity</h2>
                  </div>

                  <p>Track investigations and engineering tasks</p>
                </div>

                <button
                  className="subtle-button"
                  onClick={() => selectNavigation("Agent runs")}
                >
                  View all <span>→</span>
                </button>
              </div>

              <div className="activity-table">
                <div className="activity-table-head">
                  <span>TASK</span>
                  <span>STATUS</span>
                  <span>UPDATED</span>
                </div>

                {filteredRuns.length === 0 ? (
                  <div className="empty-state">
                    <span>⌕</span>
                    <strong>No matching tasks</strong>
                    <p>Try another search term or create a task.</p>
                  </div>
                ) : (
                  filteredRuns.map((run) => (
                    <article className="run-row" key={run.id}>
                      <div className="run-main">
                        <div
                          className={`run-type-icon run-type-${run.type
                            .toLowerCase()
                            .replaceAll(" ", "-")}`}
                        >
                          {run.type === "Test generation"
                            ? "✓"
                            : run.type === "Code review"
                              ? "⇄"
                              : "⌕"}
                        </div>

                        <div className="run-copy">
                          <strong>{run.title}</strong>

                          <span>
                            {run.repository}
                            <span className="run-separator"> · </span>
                            {run.type}
                          </span>
                        </div>
                      </div>

                      <StatusBadge status={run.status} />

                      <span className="run-time">{run.time}</span>
                    </article>
                  ))
                )}
              </div>

              <div className="panel-footer">
                <span>Showing local preview activity</span>

                <button
                  onClick={() =>
                    setNotice(
                      "Agent activity will sync with the FastAPI backend in a later integration step."
                    )
                  }
                >
                  Sync status <span>↗</span>
                </button>
              </div>
            </section>

            <div className="right-column">
              <section className="panel workflow-panel">
                <div className="panel-heading compact-heading">
                  <div>
                    <div className="heading-with-icon">
                      <span className="panel-title-icon violet-symbol">
                        ⌘
                      </span>
                      <h2>Engineering workflow</h2>
                    </div>

                    <p>From request to verified change</p>
                  </div>
                </div>

                <div className="workflow-steps">
                  {[
                    {
                      number: "01",
                      title: "Understand",
                      text: "Map repository context",
                      tone: "tone-purple",
                      symbol: "⌕",
                    },
                    {
                      number: "02",
                      title: "Plan",
                      text: "Break work into actions",
                      tone: "tone-blue",
                      symbol: "≋",
                    },
                    {
                      number: "03",
                      title: "Execute",
                      text: "Use scoped engineering tools",
                      tone: "tone-cyan",
                      symbol: "↗",
                    },
                    {
                      number: "04",
                      title: "Validate",
                      text: "Test and review changes",
                      tone: "tone-green",
                      symbol: "✓",
                    },
                  ].map((step, index) => (
                    <div className="workflow-step" key={step.number}>
                      <div className={`workflow-symbol ${step.tone}`}>
                        {step.symbol}
                      </div>

                      <div className="workflow-copy">
                        <strong>{step.title}</strong>
                        <span>{step.text}</span>
                      </div>

                      <span className="workflow-number">
                        {step.number}
                      </span>

                      {index !== 3 && (
                        <span className="workflow-connector" />
                      )}
                    </div>
                  ))}
                </div>

                <div className="workflow-note">
                  <span>✳</span>
                  <p>
                    Human review and safe execution remain essential at
                    every stage.
                  </p>
                </div>
              </section>

              <section className="connection-card">
                <div className="connection-head">
                  <div className="connection-icon">⌘</div>

                  <div>
                    <strong>Backend connection</strong>
                    <span>Live health endpoint</span>
                  </div>
                </div>

                <div
                  className={`connection-state connection-${backendStatus}`}
                  role="status"
                  aria-live="polite"
                >
                  <span
                    className={`state-pending-dot state-${backendStatus}`}
                  />

                  <span>
                    {backendStatus === "connected"
                      ? "Connected to FastAPI"
                      : backendStatus === "offline"
                        ? "Backend unavailable"
                        : "Checking backend..."}
                  </span>
                </div>

                <p>
                  {backendStatus === "connected"
                    ? `${backendService} is healthy. Repository data and agent execution still need API integration.`
                    : backendStatus === "offline"
                      ? `${backendService}. Check that your backend server is running.`
                      : "Checking the live backend health endpoint."}
                </p>
              </section>
            </div>
          </div>

          <footer className="app-footer">
            <span>
              <span className="footer-mark">✳</span> ENGINE
              <span>OS</span>
            </span>

            <span>AI Software Engineering Agent Platform</span>
            <span>Local development · Not deployed</span>
          </footer>
        </div>
      </main>

      {showTask && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowTask(false);
            }
          }}
        >
          <section
            className="task-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="task-modal-title"
          >
            <div className="modal-heading">
              <div>
                <span className="modal-kicker">
                  ENGINEERING WORKSPACE
                </span>

                <h2 id="task-modal-title">Create a task</h2>

                <p>
                  Describe the work you&apos;d like the agent to investigate.
                </p>
              </div>

              <button
                className="modal-close"
                onClick={() => setShowTask(false)}
                aria-label="Close dialog"
              >
                ×
              </button>
            </div>

            <form onSubmit={createTask}>
              <label className="field-label" htmlFor="task-title">
                Task description
              </label>

              <textarea
                id="task-title"
                required
                autoFocus
                rows={3}
                placeholder="Example: Find why repository indexing fails on large Python projects..."
                value={taskTitle}
                onChange={(event) => setTaskTitle(event.target.value)}
              />

              <label className="field-label" htmlFor="task-type">
                Task type
              </label>

              <select
                id="task-type"
                value={taskType}
                onChange={(event) => setTaskType(event.target.value)}
              >
                <option>Investigate a bug</option>
                <option>Explain a codebase</option>
                <option>Review a change</option>
                <option>Generate tests</option>
                <option>Plan code changes</option>
              </select>

              <label className="field-label" htmlFor="repository-name">
                Repository (optional)
              </label>

              <input
                id="repository-name"
                placeholder="Repository name or local workspace"
                value={repository}
                onChange={(event) => setRepository(event.target.value)}
              />

              <div className="modal-preview-note">
                <span>ⓘ</span>
                This creates a local preview task only. It does not call the
                backend yet.
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => setShowTask(false)}
                >
                  Cancel
                </button>

                <button type="submit" className="primary-button">
                  Add preview task <span>→</span>
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}