import { useState } from "react";
import { clearToken, getToken } from "./api";
import Auth from "./pages/Auth.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Explain from "./pages/Explain.jsx";
import Monitoring from "./pages/Monitoring.jsx";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!getToken());
  const [tab, setTab] = useState("dashboard");

  function logout() {
    clearToken();
    setLoggedIn(false);
  }

  if (!loggedIn) return <Auth onLogin={() => setLoggedIn(true)} />;

  return (
    <div className="container">
      <header className="topbar">
        <h1>Deploy Platform</h1>
        <nav>
          <button className={tab === "dashboard" ? "tab active" : "tab"} onClick={() => setTab("dashboard")}>
            Projects
          </button>
          <button className={tab === "monitoring" ? "tab active" : "tab"} onClick={() => setTab("monitoring")}>
            Monitoring
          </button>
          <button className={tab === "explain" ? "tab active" : "tab"} onClick={() => setTab("explain")}>
            Explain an error
          </button>
          <button className="tab" onClick={logout}>Log out</button>
        </nav>
      </header>
      {tab === "dashboard" && <Dashboard onLogout={logout} />}
      {tab === "monitoring" && <Monitoring onLogout={logout} />}
      {tab === "explain" && <Explain onLogout={logout} />}
    </div>
  );
}
