import { useState } from "react";
import { api } from "../api";

export default function Explain({ onLogout }) {
  const [log, setLog] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setBusy(true);
    try {
      setResult(await api("/explain", { method: "POST", body: { log } }));
    } catch (err) {
      if (err.status === 401) onLogout();
      else setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form className="card" onSubmit={submit}>
        <h2>Explain an error</h2>
        <p className="muted">
          Paste an error log. Passwords, keys, tokens and emails are removed automatically before anything else happens.
        </p>
        <textarea rows={8} value={log} onChange={(e) => setLog(e.target.value)} required maxLength={10000} />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>Explain</button>
      </form>

      {result && (
        <div className="card">
          {result.results.map((r, i) => (
            <div key={i}>
              <h3>{r.title}</h3>
              <p>{r.explanation}</p>
              <strong>Things to check:</strong>
              <ul>{r.checks.map((c, j) => <li key={j}>{c}</li>)}</ul>
            </div>
          ))}
          <p className="muted">{result.disclaimer}</p>
          <details>
            <summary>Cleaned log that was analysed</summary>
            <pre>{result.sanitized_log}</pre>
          </details>
        </div>
      )}
    </>
  );
}
