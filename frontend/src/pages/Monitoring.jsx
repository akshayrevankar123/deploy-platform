import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

function formatUptime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m ${seconds % 60}s`;
}

function Meter({ label, value }) {
  const level = value >= 90 ? "red" : value >= 70 ? "amber" : "green";
  return (
    <div className="meter">
      <div className="row"><span>{label}</span><strong>{value}%</strong></div>
      <div className="bar"><div className={`fill ${level}`} style={{ width: `${Math.min(value, 100)}%` }} /></div>
    </div>
  );
}

function ProjectHealth({ project, onLogout }) {
  const [summary, setSummary] = useState(null);
  const [checks, setChecks] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setSummary(await api(`/monitoring/projects/${project.id}/summary`));
      setChecks(await api(`/monitoring/projects/${project.id}/checks`));
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    }
  }, [project.id, onLogout]);

  useEffect(() => { load(); }, [load]);

  async function checkNow() {
    setBusy(true);
    setError("");
    try {
      await api(`/monitoring/projects/${project.id}/check`, { method: "POST" });
      await load();
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="row">
        <div>
          <h3>{project.name}</h3>
          {project.live_url
            ? <a href={project.live_url} target="_blank" rel="noreferrer noopener">{project.live_url}</a>
            : <span className="muted">Not deployed yet. Nothing to monitor.</span>}
        </div>
        {summary?.last_ok !== null && summary?.last_ok !== undefined && (
          <span className={summary.last_ok ? "badge green" : "badge red"}>{summary.last_ok ? "UP" : "DOWN"}</span>
        )}
      </div>

      {summary && summary.total_checks > 0 && (
        <p>
          Uptime: <strong>{summary.uptime_percent}%</strong> over the last {summary.total_checks} checks
          {summary.avg_response_ms !== null && <> | average response <strong>{summary.avg_response_ms} ms</strong></>}
        </p>
      )}

      <button disabled={busy || !project.live_url} onClick={checkNow}>Check now</button>
      {error && <p className="error">{error}</p>}

      {checks.length > 0 && (
        <ul className="findings">
          {checks.slice(0, 8).map((c) => (
            <li key={c.id}>
              <span className={c.ok ? "badge green" : "badge red"}>{c.ok ? "OK" : "FAIL"}</span>{" "}
              {c.response_ms !== null ? `${c.response_ms} ms` : c.error}
              <div className="muted">{new Date(c.created_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Monitoring({ onLogout }) {
  const [stats, setStats] = useState(null);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");

  const loadStats = useCallback(async () => {
    try {
      setStats(await api("/monitoring/system"));
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    }
  }, [onLogout]);

  useEffect(() => {
    loadStats();
    api("/projects").then(setProjects).catch((err) => {
      if (err.status === 401) onLogout();
      else setError(err.message);
    });
    const timer = setInterval(loadStats, 10000); // refresh every 10 seconds
    return () => clearInterval(timer);
  }, [loadStats, onLogout]);

  return (
    <>
      <div className="card">
        <h2>Server resources</h2>
        <p className="muted">The machine this backend runs on. Refreshes every 10 seconds.</p>
        {error && <p className="error">{error}</p>}
        {stats && (
          <>
            <Meter label="CPU" value={stats.cpu_percent} />
            <Meter label={`Memory (${stats.memory_used_mb} MB used)`} value={stats.memory_percent} />
            <Meter label="Disk" value={stats.disk_percent} />
            <p className="muted">App uptime: {formatUptime(stats.app_uptime_seconds)}</p>
          </>
        )}
      </div>

      <h2>Project health</h2>
      {projects.length === 0 && <p className="muted">No projects yet.</p>}
      {projects.map((p) => <ProjectHealth key={p.id} project={p} onLogout={onLogout} />)}
    </>
  );
}
