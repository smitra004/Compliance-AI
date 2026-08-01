import React, { useState } from "react";
import { Layers, RefreshCw, Eye, CheckCircle2, Shield, Lock, Activity } from "lucide-react";

export default function EnterprisePolicyRegistry({ CAP, policies, fetchPolicies, handleStatusChange, reloadStatus, handleReloadPolicies }) {
  const [inspectPolicy, setInspectPolicy] = useState(null);

  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
    },
    badge: (type) => ({
      padding: "4px 10px",
      borderRadius: 16,
      fontSize: 11,
      fontWeight: 700,
      textTransform: "uppercase",
      background: type === "Published" ? "rgba(90, 122, 106, 0.15)" : type === "Review" ? "rgba(194, 104, 62, 0.15)" : "rgba(201, 169, 110, 0.15)",
      color: type === "Published" ? "#5A7A6A" : type === "Review" ? "#C2683E" : CAP?.purple || "#C9A96E",
      border: `1px solid ${type === "Published" ? "#5A7A6A" : type === "Review" ? "#C2683E" : CAP?.purple || "#C9A96E"}`,
    }),
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: CAP?.text }}>Enterprise Policy Registry</h3>
          <p style={{ margin: 0, fontSize: 13, color: CAP?.textDim }}>Lifecycle Management (Draft → Review → Approved → Published)</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {reloadStatus && <span style={{ fontSize: 12, color: CAP?.purple }}>{reloadStatus}</span>}
          <button onClick={handleReloadPolicies} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.panel, color: CAP?.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
            <RefreshCw size={14} /> Hot Reload Policies
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))", gap: 16 }}>
        {policies.map((pol) => (
          <div key={pol.policy_id} style={{ padding: 16, borderRadius: 12, border: `1px solid ${CAP?.border}`, background: CAP?.bg }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 800, color: CAP?.purple }}>{pol.policy_id}</span>
              <span style={styles.badge(pol.status || "Published")}>{pol.status || "Published"}</span>
            </div>

            <h4 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 4px 0", color: CAP?.text }}>{pol.name}</h4>
            <p style={{ fontSize: 12, color: CAP?.textDim, margin: "0 0 10px 0", lineHeight: 1.4 }}>{pol.description}</p>

            <div style={{ fontSize: 11, color: CAP?.textDim, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: 12, background: CAP?.panel, padding: 8, borderRadius: 6 }}>
              <div><strong>Priority:</strong> {pol.priority}</div>
              <div><strong>Version:</strong> {pol.version || "v1.0.0"}</div>
              <div><strong>Effect:</strong> {pol.effect}</div>
              <div><strong>Risk Limit:</strong> {pol.max_risk_score || 80}</div>
              <div style={{ gridColumn: "span 2" }}><strong>Owner:</strong> {pol.owner || "security-admin@corp.com"}</div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                onClick={() => setInspectPolicy(pol)}
                style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 10px", borderRadius: 6, border: `1px solid ${CAP?.border}`, background: CAP?.panel, fontSize: 12, color: CAP?.text, cursor: "pointer" }}
              >
                <Eye size={12} /> Inspect Policy
              </button>

              <div style={{ display: "flex", gap: 4 }}>
                {pol.status === "Draft" && (
                  <button onClick={() => handleStatusChange(pol.policy_id, "Review")} style={{ padding: "4px 8px", borderRadius: 4, background: "rgba(194, 104, 62, 0.15)", color: "#C2683E", border: "none", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>Submit Review</button>
                )}
                {pol.status === "Review" && (
                  <button onClick={() => handleStatusChange(pol.policy_id, "Approved")} style={{ padding: "4px 8px", borderRadius: 4, background: "rgba(90, 122, 106, 0.15)", color: "#5A7A6A", border: "none", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>Approve</button>
                )}
                {pol.status === "Approved" && (
                  <button onClick={() => handleStatusChange(pol.policy_id, "Published")} style={{ padding: "4px 8px", borderRadius: 4, background: "#5A7A6A", color: "#FFFFFF", border: "none", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>Publish</button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Inspect Policy Modal */}
      {inspectPolicy && (
        <div style={{ marginTop: 20, padding: 18, borderRadius: 12, border: `1px solid ${CAP?.purple}`, background: CAP?.bg }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <h4 style={{ margin: 0, fontSize: 15, color: CAP?.purple }}>Inspect Rule Definition: {inspectPolicy.policy_id}</h4>
            <button onClick={() => setInspectPolicy(null)} style={{ border: "none", background: "transparent", color: CAP?.text, cursor: "pointer", fontWeight: 700 }}>✕ Close</button>
          </div>
          <pre style={{ background: "#16120E", color: "#E6DACE", padding: 14, borderRadius: 8, fontSize: 12, overflowX: "auto", margin: 0 }}>
            {JSON.stringify(inspectPolicy, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
