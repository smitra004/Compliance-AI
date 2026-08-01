import React from "react";
import { Cpu, Play, RefreshCw } from "lucide-react";

export default function PolicySandbox({ CAP, realUsers, user, setUser, role, setRole, department, setDepartment, action, setAction, clearanceLevel, setClearanceLevel, mfaStatus, setMfaStatus, vpnConnected, setVpnConnected, businessHours, setBusinessHours, classification, setClassification, containsPii, setContainsPii, containsFin, setContainsFin, country, setCountry, loading, runSimulation }) {
  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
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
    input: {
      width: "100%",
      padding: "8px 12px",
      borderRadius: 8,
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.12)"}`,
      background: CAP?.bg || "#FAF7F2",
      color: CAP?.text || "#16120E",
      fontSize: 13,
      outline: "none",
    },
  };

  return (
    <div style={styles.card}>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 0, marginBottom: 16, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
        <Cpu size={18} color={CAP?.purple} /> Administrator Simulation Testing Controls
      </h3>

      <div style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: CAP?.purple, textTransform: "uppercase", display: "block", marginBottom: 8 }}>
          1. Subject Attributes
        </span>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <label style={styles.label}>User (from User Management)</label>
            {Array.isArray(realUsers) && realUsers.length > 0 ? (
              <select
                style={styles.input}
                value={user}
                onChange={(e) => {
                  const picked = realUsers.find((u) => u.username === e.target.value);
                  setUser(e.target.value);
                  if (picked) {
                    if (picked.role) setRole(picked.role);
                    if (picked.department) setDepartment(picked.department);
                  }
                }}
              >
                {realUsers.map((u) => (
                  <option key={u.id ?? u.username} value={u.username}>
                    {u.username} · {u.role}{u.department ? ` · ${u.department}` : ""}
                  </option>
                ))}
              </select>
            ) : (
              <input style={styles.input} value={user} onChange={(e) => setUser(e.target.value)} />
            )}
          </div>
          <div>
            <label style={styles.label}>Role</label>
            <select style={styles.input} value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="central_admin">Central Admin</option>
              <option value="admin">Department Admin</option>
              <option value="manager">Manager</option>
              <option value="auditor">Auditor</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div>
            <label style={styles.label}>Department</label>
            <select style={styles.input} value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="Finance">Finance</option>
              <option value="HR">HR</option>
              <option value="Legal">Legal</option>
              <option value="Operations">Operations</option>
              <option value="Security">Security</option>
            </select>
          </div>
          <div>
            <label style={styles.label}>Clearance Level</label>
            <select style={styles.input} value={clearanceLevel} onChange={(e) => setClearanceLevel(e.target.value)}>
              <option value="Public">Public (Rank 1)</option>
              <option value="Internal">Internal (Rank 2)</option>
              <option value="Confidential">Confidential (Rank 3)</option>
              <option value="Restricted">Restricted (Rank 4)</option>
              <option value="Top Secret">Top Secret (Rank 5)</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: CAP?.purple, textTransform: "uppercase", display: "block", marginBottom: 8 }}>
          2. Target Action & Resource Metadata
        </span>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <label style={styles.label}>Target Action</label>
            <select style={styles.input} value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="Read">Read / View</option>
              <option value="Upload">Upload Document</option>
              <option value="Download">Download Document</option>
              <option value="Delete">Delete Resource</option>
              <option value="Export">Export Data Stream</option>
            </select>
          </div>
          <div>
            <label style={styles.label}>Classification</label>
            <select style={styles.input} value={classification} onChange={(e) => setClassification(e.target.value)}>
              <option value="Public">Public</option>
              <option value="Internal">Internal</option>
              <option value="Confidential">Confidential</option>
              <option value="Restricted">Restricted</option>
              <option value="Top Secret">Top Secret</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: CAP?.purple, textTransform: "uppercase", display: "block", marginBottom: 8 }}>
          3. Environmental Context
        </span>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: CAP?.text, cursor: "pointer" }}>
            <input type="checkbox" checked={vpnConnected} onChange={(e) => setVpnConnected(e.target.checked)} />
            VPN Connected
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: CAP?.text, cursor: "pointer" }}>
            <input type="checkbox" checked={businessHours} onChange={(e) => setBusinessHours(e.target.checked)} />
            Business Hours
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: CAP?.text, cursor: "pointer" }}>
            <input type="checkbox" checked={mfaStatus} onChange={(e) => setMfaStatus(e.target.checked)} />
            MFA Verified
          </label>
          <div>
            <label style={styles.label}>Country Origin</label>
            <input style={styles.input} value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
        </div>
      </div>

      <button
        onClick={runSimulation}
        disabled={loading}
        style={{
          width: "100%",
          padding: "11px 18px",
          borderRadius: 8,
          border: "none",
          background: CAP?.purple || "#C9A96E",
          color: "#16120E",
          fontSize: 13,
          fontWeight: 700,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
        }}
      >
        {loading ? <RefreshCw className="spin" size={16} /> : <Play size={16} />}
        Run ABAC Policy Simulation
      </button>
    </div>
  );
}
