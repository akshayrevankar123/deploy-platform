import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const BADGE = {
  CRITICAL: "badge red",
  ERROR: "badge red",
  WARNING: "badge amber",
  INFO: "badge blue",
};

function ProjectCard({ project, onChanged, onLogout }) {
  const [scans, setScans] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setScans(await api(`/projects/${project.id}/scans`));
      setDeployments(await api(`/projects/${project.id}/deployments`));
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    }
  }, [project.id, onLogout]);

  useEffect(() => { load(); }, [load]);

  async function act(path) {
    setBusy(true);
    setError("");
    try {
      await api(path, { method: "POST" });
      await load();
      onChanged();
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const latestScan = scans[0];

  return (
    <div className="card">
      <div className="row">
        <div>
          <h3>{project.name}</h3>
          <a href={project.repo_url} target="_blank" rel="noreferrer noopener">{project.repo_url}</a>
        </div>
        <span className="badge grey">{project.status.replaceAll("_", " ")}</span>
      </div>

      <p>
        Live URL: {project.live_url ? <a href={project.live_url} target="_blank" rel="noreferrer noopener">{project.live_url}</a> : <span className="muted">not deployed yet</span>}
      </p>

      <div className="actions">
        <button disabled={busy} onClick={() => act(`/projects/${project.id}/scan`)}>Scan project</button>
        <button disabled={busy} className="secondary" onClick={() => act(`/projects/${project.id}/deploy`)}>Deploy project</button>
      </div>
      {error && <p className="error">{error}</p>}

      <h4>Security / readiness results</h4>
      {!latestScan && <p className="muted">No scan yet. Click "Scan project".</p>}
      {latestScan && (
        <>
          <p>Latest scan: <strong>{latestScan.status}</strong> <span className="muted">({new Date(latestScan.created_at).toLocaleString()})</span></p>
          {latestScan.findings.length === 0 && <p className="success">No problems found in this quick check. This is not a guarantee of security.</p>}
          <ul className="findings">
            {latestScan.findings.map((f, i) => (
              <li key={i}>
                <span className={BADGE[f.severity] || "badge grey"}>{f.severity}</span> <strong>{f.title}</strong>
                <div className="muted">{f.detail}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h4>Deployment history</h4>
      {deployments.length === 0 && <p className="muted">No deployments yet.</p>}
      <ul className="findings">
        {deployments.map((d) => (
          <li key={d.id}>
            <span className="badge grey">{d.status}</span> {d.message}
            <div className="muted">{new Date(d.created_at).toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard({ onLogout }) {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState("");

  const loadProjects = useCallback(async () => {
    try {
      setProjects(await api("/projects"));
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    }
  }, [onLogout]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  async function createProject(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/projects", { method: "POST", body: { name, repo_url: repoUrl } });
      setName("");
      setRepoUrl("");
      loadProjects();
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    }
  }

  return (
    <>
      <form className="card" onSubmit={createProject}>
        <h2>Register a project</h2>
        <label>
          Project name
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} />
        </label>
        <label>
          GitHub repository URL
          <input
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/your-name/your-repo"
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit">Add project</button>
      </form>

      <h2>Your projects</h2>
      {projects.length === 0 && <p className="muted">No projects yet. Add one above.</p>}
      {projects.map((p) => (
        <ProjectCard key={p.id} project={p} onChanged={loadProjects} onLogout={onLogout} />
      ))}
    </>
  );
}
