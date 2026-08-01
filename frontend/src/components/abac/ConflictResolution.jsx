import React from "react";
import { Layers, ArrowRight, ShieldCheck, ShieldAlert, CheckCircle2 } from "lucide-react";

export default function ConflictResolution({ CAP, evalData }) {
  const matchedPolicy = evalData?.matched_policy || "FIN-001";
  const decision = evalData?.decision || "PERMIT";
  const evaluatedPolicies = evalData?.evaluated_policies || ["FIN-001", "GLOB-001", "SEC-002"];

  const conflicts = [
    { id: matchedPolicy, effect: decision, priority: 50, status: "WINNING POLICY", reason: "Highest priority matched policy for Finance department." },
    { id: "GLOB-001", effect: "PERMIT", priority: 10, status: "OVERRIDDEN", reason: "Global fallback baseline overridden by higher priority policy." },
    { id: "SEC-002", effect: "DENY", priority: 90, status: "NOT MATCHED", reason: "Condition 'Top Secret' classification not satisfied by resource." },
  ];

  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
      marginBottom: 20,
    },
    badge: (status) => ({
      padding: "3px 8px",
      borderRadius: 12,
      fontSize: 10,
      fontWeight: 800,
      background: status === "WINNING POLICY" ? "rgba(90, 122, 106, 0.15)" : "rgba(201, 169, 110, 0.15)",
      color: status === "WINNING POLICY" ? "#5A7A6A" : CAP?.purple || "#C9A96E",
      border: `1px solid ${status === "WINNING POLICY" ? "#5A7A6A" : CAP?.purple || "#C9A96E"}`,
    }),
  };

  return (
    <div style={styles.card}>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 0, marginBottom: 14, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
        <Layers size={18} color={CAP?.purple} /> Policy Conflict Precedence & Resolution Trace
      </h3>

      {/* Diagram Flow */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, overflowX: "auto", padding: "10px 0" }}>
        <div style={{ padding: "8px 12px", borderRadius: 8, background: CAP?.bg, border: `1px solid ${CAP?.border}`, fontSize: 12, fontWeight: 700 }}>
          Matched Policies ({evaluatedPolicies.length})
        </div>
        <ArrowRight size={16} color={CAP?.purple} />
        <div style={{ padding: "8px 12px", borderRadius: 8, background: CAP?.bg, border: `1px solid ${CAP?.border}`, fontSize: 12, fontWeight: 700 }}>
          Conflict Detection Engine
        </div>
        <ArrowRight size={16} color={CAP?.purple} />
        <div style={{ padding: "8px 12px", borderRadius: 8, background: CAP?.bg, border: `1px solid ${CAP?.border}`, fontSize: 12, fontWeight: 700 }}>
          Deny-Overrides & Priority Precedence
        </div>
        <ArrowRight size={16} color={CAP?.purple} />
        <div style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(90, 122, 106, 0.15)", border: "1px solid #5A7A6A", color: "#5A7A6A", fontSize: 12, fontWeight: 800 }}>
          Winning Policy: {matchedPolicy} ({decision})
        </div>
      </div>

      {/* Precedence Breakdown Table */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {conflicts.map((c) => (
          <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderRadius: 8, background: CAP?.bg, border: `1px solid ${CAP?.border}`, fontSize: 12 }}>
            <div>
              <span style={{ fontWeight: 800, color: CAP?.purple }}>{c.id}</span> ({c.effect}) - Priority: <strong>{c.priority}</strong>
              <div style={{ fontSize: 11, color: CAP?.textDim }}>{c.reason}</div>
            </div>
            <span style={styles.badge(c.status)}>{c.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
