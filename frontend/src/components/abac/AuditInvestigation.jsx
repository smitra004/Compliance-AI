import React, { useState, useEffect } from "react";
import { Activity, Search, Filter, Eye, RefreshCw, Lock, ShieldCheck } from "lucide-react";

export default function AuditInvestigation({ token, CAP }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("All");
  const [decision, setDecision] = useState("All");

  const authToken = token || localStorage.getItem("token") || "";

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      let url = `/api/v1/abac/audit-logs?limit=50&department=${department}&decision=${decision}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const res = await fetch(url, { headers });
      const data = await res.json();
      if (Array.isArray(data)) setLogs(data);
    } catch (err) {
      console.error("Audit log error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [department, decision, search]);

  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
      marginBottom: 20,
    },
    label: {
      fontSize: 12,
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: CAP?.textDim || "#5C5248",
      marginBottom: 4,
      display: "block",
    },
    badge: (dec) => ({
      padding: "3px 8px",
      borderRadius: 12,
      fontSize: 11,
      fontWeight: 800,
      background: dec === "PERMIT" ? "rgba(90, 122, 106, 0.15)" : "rgba(184, 92, 56, 0.15)",
      color: dec === "PERMIT" ? "#5A7A6A" : "#B85C38",
      border: `1px solid ${dec === "PERMIT" ? "#5A7A6A" : "#B85C38"}`,
    }),
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: CAP?.text }}>Immutable Forensic Audit Logs & Investigation</h3>
          <p style={{ margin: 0, fontSize: 13, color: CAP?.textDim }}>Captured 25+ forensic parameters per request with HMAC-SHA256 signatures</p>
        </div>
        <button onClick={fetchLogs} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.panel, color: CAP?.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
          <RefreshCw size={14} /> Refresh Logs
        </button>
      </div>

      {/* Multi-Column Search & Filters */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div>
          <label style={styles.label}>Search User / Action / Policy / Resource</label>
          <input
            style={{
              width: "100%",
              padding: "8px 12px",
              borderRadius: 8,
              border: `1px solid ${CAP?.border}`,
              background: CAP?.bg,
              color: CAP?.text,
              fontSize: 13,
              outline: "none",
            }}
            placeholder="Type search query..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <label style={styles.label}>Department Filter</label>
          <select style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.bg, color: CAP?.text, fontSize: 13 }} value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="All">All Departments</option>
            <option value="Finance">Finance</option>
            <option value="HR">HR</option>
            <option value="Legal">Legal</option>
            <option value="Security">Security</option>
          </select>
        </div>
        <div>
          <label style={styles.label}>Decision Filter</label>
          <select style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.bg, color: CAP?.text, fontSize: 13 }} value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="All">All Decisions</option>
            <option value="PERMIT">PERMIT</option>
            <option value="DENY">DENY</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: `2px solid ${CAP?.border}`, textAlign: "left", color: CAP?.textDim }}>
            <th style={{ padding: "10px 12px" }}>Timestamp</th>
            <th style={{ padding: "10px 12px" }}>User</th>
            <th style={{ padding: "10px 12px" }}>Action</th>
            <th style={{ padding: "10px 12px" }}>Matched Policy</th>
            <th style={{ padding: "10px 12px" }}>Verdict</th>
            <th style={{ padding: "10px 12px" }}>Risk</th>
            <th style={{ padding: "10px 12px" }}>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} style={{ borderBottom: `1px solid ${CAP?.border}` }}>
              <td style={{ padding: "10px 12px", color: CAP?.textDim }}>{log.timestamp ? log.timestamp.split("T")[1]?.slice(0, 8) : "-"}</td>
              <td style={{ padding: "10px 12px", fontWeight: 600, color: CAP?.text }}>{log.user} ({log.role})</td>
              <td style={{ padding: "10px 12px", color: CAP?.text }}>{log.action}</td>
              <td style={{ padding: "10px 12px", fontWeight: 700, color: CAP?.purple }}>{log.matched_policy || "GLOB-001"}</td>
              <td style={{ padding: "10px 12px" }}><span style={styles.badge(log.decision)}>{log.decision}</span></td>
              <td style={{ padding: "10px 12px", fontWeight: 700, color: log.risk_score > 60 ? "#B85C38" : "#5A7A6A" }}>{log.risk_score}</td>
              <td style={{ padding: "10px 12px" }}>
                <button onClick={() => setSelectedLog(log)} style={{ padding: "4px 10px", borderRadius: 6, border: `1px solid ${CAP?.border}`, background: CAP?.panel, fontSize: 12, color: CAP?.text, cursor: "pointer" }}>Inspect JSON</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Forensic Modal */}
      {selectedLog && (
        <div style={{ marginTop: 20, padding: 18, borderRadius: 12, border: `1px solid ${CAP?.purple}`, background: CAP?.bg }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h4 style={{ margin: 0, fontSize: 15, color: CAP?.purple }}>25+ Attribute Forensic Investigation Modal</h4>
            <button onClick={() => setSelectedLog(null)} style={{ border: "none", background: "transparent", color: CAP?.text, cursor: "pointer", fontWeight: 700 }}>✕ Close</button>
          </div>
          <pre style={{ background: "#16120E", color: "#E6DACE", padding: 14, borderRadius: 8, fontSize: 12, overflowX: "auto", margin: 0 }}>
            {JSON.stringify(selectedLog, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
