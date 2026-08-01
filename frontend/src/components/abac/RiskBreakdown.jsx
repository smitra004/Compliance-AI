import React, { useState } from "react";
import { Zap, AlertTriangle, ShieldCheck, ShieldAlert, Info, ChevronDown, ChevronRight } from "lucide-react";

export default function RiskBreakdown({ CAP, riskScore, riskLevel, riskBreakdown }) {
  const [selectedFactor, setSelectedFactor] = useState(null);

  const score = riskScore || 5;
  const level = riskLevel || "Low";
  const factors = riskBreakdown || [
    { factor: "VPN / Network Location", status: "PASS", points: 0, reason: "Request originated from encrypted Corporate VPN tunnel." },
    { factor: "MFA Verification Status", status: "PASS", points: 0, reason: "Multi-Factor Authentication verified on current IdP session." },
    { factor: "Business Hours Policy", status: "PASS", points: 0, reason: "Request received within standard operating business hours." },
    { factor: "Device Trust & Management", status: "PASS", points: 0, reason: "Device MDM compliance check passed." },
    { factor: "Geolocation / IP Reputation", status: "PASS", points: 0, reason: "IP address reputation score within trusted threshold." },
    { factor: "Request Velocity Rate", status: "PASS", points: 0, reason: "API request frequency (12 req/min) within normal limits." },
  ];

  const getMeterColor = (val) => {
    if (val > 75) return "#B85C38";
    if (val > 40) return "#C2683E";
    return "#5A7A6A";
  };

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
      background: status === "PASS" ? "rgba(90, 122, 106, 0.15)" : status === "WARNING" ? "rgba(194, 104, 62, 0.15)" : "rgba(184, 92, 56, 0.15)",
      color: status === "PASS" ? "#5A7A6A" : status === "WARNING" ? "#C2683E" : "#B85C38",
      border: `1px solid ${status === "PASS" ? "#5A7A6A" : status === "WARNING" ? "#C2683E" : "#B85C38"}`,
    }),
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
          <Zap size={18} color={CAP?.purple} /> Enhanced Enterprise Risk Engine & Factor Breakdown
        </h3>
        <span style={{ fontSize: 14, fontWeight: 800, color: getMeterColor(score) }}>
          Score: {score} / 100 ({level} Risk)
        </span>
      </div>

      {/* Visual Risk Gauge Meter Progress Bar */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 700, color: CAP?.textDim, marginBottom: 4 }}>
          <span>0 (Low Risk)</span>
          <span>40 (Medium)</span>
          <span>75 (High)</span>
          <span>100 (Critical Block)</span>
        </div>
        <div style={{ height: 10, borderRadius: 5, background: CAP?.bg, border: `1px solid ${CAP?.border}`, overflow: "hidden", position: "relative" }}>
          <div
            style={{
              height: "100%",
              width: `${Math.min(score, 100)}%`,
              background: getMeterColor(score),
              transition: "width 0.4s ease",
            }}
          />
        </div>
      </div>

      {/* Evaluated Factors List */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 10 }}>
        {factors.map((f, i) => {
          const isSelected = selectedFactor === i;
          return (
            <div
              key={i}
              onClick={() => setSelectedFactor(isSelected ? null : i)}
              style={{
                padding: 10,
                borderRadius: 8,
                border: `1px solid ${isSelected ? CAP?.purple || "#C9A96E" : CAP?.border}`,
                background: isSelected ? "rgba(201, 169, 110, 0.06)" : CAP?.bg,
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: CAP?.text }}>{f.factor}</span>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={styles.badge(f.status)}>{f.status} (+{f.points || 0})</span>
                  {isSelected ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </div>
              </div>

              <div style={{ fontSize: 11, color: CAP?.textDim }}>{f.reason || "Evaluated against Zero Trust policy limits."}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
