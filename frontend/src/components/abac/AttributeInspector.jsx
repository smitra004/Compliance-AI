import React, { useState } from "react";
import { Sliders, User, Database, Globe, Zap, Layers } from "lucide-react";

export default function AttributeInspector({ CAP, evalData }) {
  const [activeGroup, setActiveGroup] = useState("subject");

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  })();

  const currentUsername = storedUser.username || "admin";
  const currentRole = storedUser.role || "central_admin";
  const currentDept = storedUser.department || "Global";

  const subjectAttrs = evalData?.subject || {
    username: currentUsername,
    role: currentRole,
    department: currentDept,
    clearance_level: "Confidential",
    clearance_rank: 3,
    designation: storedUser.designation || "Compliance Manager",
    region: "US",
    business_unit: "Corporate",
    mfa_status: true,
  };


  const resourceAttrs = evalData?.resource || {
    resource_id: "RES-DOC-101",
    department: "Finance",
    classification: "Restricted",
    contains_pii: true,
    contains_financial_data: true,
  };

  const envAttrs = evalData?.environment || {
    vpn_connected: true,
    business_hours: true,
    country: "US",
    device_managed: true,
  };

  const actionAttrs = {
    requested_action: evalData?.action || "Read",
    is_write: false,
    is_delete: false,
    is_export: false,
  };

  const riskAttrs = {
    risk_score: evalData?.risk_score || 5,
    risk_level: evalData?.risk_level || "Low",
    max_threshold: 80,
  };

  const groups = [
    { id: "subject", label: "Subject", icon: <User size={14} />, data: subjectAttrs },
    { id: "resource", label: "Resource", icon: <Database size={14} />, data: resourceAttrs },
    { id: "environment", label: "Environment", icon: <Globe size={14} />, data: envAttrs },
    { id: "action", label: "Action", icon: <Sliders size={14} />, data: actionAttrs },
    { id: "risk", label: "Risk Engine", icon: <Zap size={14} />, data: riskAttrs },
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
  };

  const currentData = groups.find((g) => g.id === activeGroup)?.data || {};

  return (
    <div style={styles.card}>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 0, marginBottom: 14, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
        <Sliders size={18} color={CAP?.purple} /> Contextual Attribute Inspector
      </h3>

      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {groups.map((g) => (
          <button
            key={g.id}
            onClick={() => setActiveGroup(g.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "6px 12px",
              borderRadius: 6,
              border: `1px solid ${activeGroup === g.id ? CAP?.purple || "#C9A96E" : CAP?.border}`,
              background: activeGroup === g.id ? CAP?.purple || "#C9A96E" : CAP?.bg,
              color: activeGroup === g.id ? "#16120E" : CAP?.textDim,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {g.icon} {g.label}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, background: CAP?.bg, padding: 12, borderRadius: 8, border: `1px solid ${CAP?.border}` }}>
        {Object.entries(currentData).map(([key, val]) => (
          <div key={key}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: CAP?.textDim }}>{key.replace(/_/g, " ")}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: CAP?.text }}>{String(val)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
