import React, { useState } from "react";
import { Activity, ChevronDown, ChevronRight, Clock, CheckCircle2 } from "lucide-react";

export default function DecisionPipeline({ CAP, pipelineData, executionTimeMs }) {
  const [expandedStep, setExpandedStep] = useState(null);

  if (!pipelineData || !Array.isArray(pipelineData)) {
    return (
      <div style={{ padding: 20, textAlign: "center", color: CAP?.textDim }}>
        No decision pipeline trace available. Run an access evaluation.
      </div>
    );
  }

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
      textTransform: "uppercase",
      background: status === "PASSED" || status === "EXECUTED" ? "rgba(90, 122, 106, 0.15)" : "rgba(184, 92, 56, 0.15)",
      color: status === "PASSED" || status === "EXECUTED" ? "#5A7A6A" : "#B85C38",
      border: `1px solid ${status === "PASSED" || status === "EXECUTED" ? "#5A7A6A" : "#B85C38"}`,
    }),
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
          <Activity size={18} color={CAP?.purple} /> 11-Stage Authorization Decision Visualizer Pipeline & Timeline
        </h3>
        <div style={{ fontSize: 12, fontWeight: 700, color: CAP?.purple, display: "flex", alignItems: "center", gap: 4 }}>
          <Clock size={14} /> Total Evaluation Duration: {executionTimeMs || 1.4} ms
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
        {pipelineData.map((step) => {
          const isExpanded = expandedStep === step.step;
          return (
            <div
              key={step.step}
              onClick={() => setExpandedStep(isExpanded ? null : step.step)}
              style={{
                padding: 12,
                borderRadius: 10,
                border: `1px solid ${isExpanded ? CAP?.purple || "#C9A96E" : CAP?.border}`,
                background: isExpanded ? "rgba(201, 169, 110, 0.06)" : CAP?.bg,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: 10, fontWeight: 800, color: CAP?.purple }}>STEP {step.step}</span>
                <span style={styles.badge(step.status)}>{step.status}</span>
              </div>

              <div style={{ fontSize: 13, fontWeight: 700, color: CAP?.text, marginBottom: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>{step.name}</span>
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </div>

              <div style={{ fontSize: 11, color: CAP?.textDim, lineHeight: 1.3 }}>{step.details}</div>

              {isExpanded && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${CAP?.border}`, fontSize: 11, color: CAP?.text }}>
                  <div style={{ fontWeight: 700, color: CAP?.purple }}>Evaluation Context Details:</div>
                  <pre style={{ background: "#16120E", color: "#5A7A6A", padding: 8, borderRadius: 6, fontSize: 10, overflowX: "auto", margin: "4px 0 0 0" }}>
                    {JSON.stringify(step, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
