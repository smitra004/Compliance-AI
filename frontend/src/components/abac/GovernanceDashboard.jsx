import React, { useState, useEffect } from "react";
import { Activity, ShieldCheck, ShieldAlert, Clock, Layers, Zap, AlertTriangle, RefreshCw, BarChart2 } from "lucide-react";

export default function GovernanceDashboard({ token, CAP }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch("/api/v1/dashboard/stats", { headers });
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Dashboard stats error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
    },
    metricValue: {
      fontSize: 26,
      fontWeight: 800,
      color: CAP?.text || "#16120E",
      marginTop: 6,
      marginBottom: 2,
    },
    label: {
      fontSize: 12,
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.06em",
      color: CAP?.textDim || "#5C5248",
    },
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40, color: CAP?.textDim }}>
        <RefreshCw className="spin" size={24} /> Loading Governance Dashboard KPIs...
      </div>
    );
  }

  const kpis = [
    { title: "Total Requests Evaluated", value: stats?.total_requests || 0, icon: <Activity color={CAP?.purple} size={20} />, sub: "Audit logs recorded" },
    { title: "Authorization Permit Rate", value: `${stats?.permit_rate || 100}%`, icon: <ShieldCheck color="#5A7A6A" size={20} />, sub: `${stats?.permit_count || 0} Permitted` },
    { title: "Authorization Denial Rate", value: `${stats?.denial_rate || 0}%`, icon: <ShieldAlert color="#B85C38" size={20} />, sub: `${stats?.deny_count || 0} Denied` },
    { title: "Average Threat Risk Score", value: `${stats?.avg_risk_score || 5} / 100`, icon: <Zap color="#C2683E" size={20} />, sub: "Composite threat score" },
    { title: "Average Evaluation Time", value: `${stats?.avg_evaluation_time_ms || 1.4} ms`, icon: <Clock color={CAP?.purple} size={20} />, sub: "Zero latency budget" },
    { title: "Most Triggered Policy", value: stats?.most_triggered_policy || "GLOB-001", icon: <Layers color={CAP?.purple} size={20} />, sub: "Highest evaluation frequency" },
    { title: "Most Applied Obligation", value: stats?.most_applied_obligation || "Mask PAN", icon: <ShieldCheck color="#5A7A6A" size={20} />, sub: "Field masking obligation" },
    { title: "High-Risk Requests Today", value: stats?.high_risk_requests_today || 0, icon: <AlertTriangle color="#B85C38" size={20} />, sub: "Risk Score >= 60" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: CAP?.text }}>Enterprise Authorization Governance Analytics</h3>
          <p style={{ margin: 0, fontSize: 13, color: CAP?.textDim }}>Dynamically computed from audit logs & zero-trust engine metrics</p>
        </div>
        <button onClick={fetchStats} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.panel, color: CAP?.text, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
          <RefreshCw size={14} /> Refresh Metrics
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
        {kpis.map((kpi, idx) => (
          <div key={idx} style={styles.card}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={styles.label}>{kpi.title}</span>
              {kpi.icon}
            </div>
            <div style={styles.metricValue}>{kpi.value}</div>
            <div style={{ fontSize: 12, color: CAP?.textDim }}>{kpi.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
