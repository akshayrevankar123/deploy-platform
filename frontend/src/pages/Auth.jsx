import { useState } from "react";
import { api, setToken } from "../api";

export default function Auth({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    setInfo("");
    try {
      if (mode === "register") {
        await api("/auth/register", { method: "POST", body: { username, password }, auth: false });
        setInfo("Account created. Please log in.");
        setMode("login");
      } else {
        const data = await api("/auth/login", { method: "POST", body: { username, password }, auth: false });
        setToken(data.access_token);
        onLogin();
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="container narrow">
      <h1>Deploy Platform</h1>
      <p className="muted">Test, scan and deploy your project, with errors explained in simple language.</p>
      <form className="card" onSubmit={submit}>
        <h2>{mode === "login" ? "Log in" : "Create account"}</h2>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        </label>
        <label>
          Password {mode === "register" && <span className="muted">(at least 8 characters)</span>}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>
        {error && <p className="error">{error}</p>}
        {info && <p className="success">{info}</p>}
        <button type="submit">{mode === "login" ? "Log in" : "Register"}</button>
        <p className="muted">
          {mode === "login" ? "New here? " : "Already have an account? "}
          <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "Create an account" : "Log in"}
          </a>
        </p>
      </form>
    </div>
  );
}
