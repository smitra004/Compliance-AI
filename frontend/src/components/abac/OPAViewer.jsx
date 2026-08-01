import React, { useState } from "react";
import { FileText, Download, Copy, Check } from "lucide-react";

export default function OPAViewer({ CAP, opaBundle }) {
  const [copied, setCopied] = useState(false);

  const regoCode = opaBundle?.policies ? opaBundle.policies["authz.rego"] : `package compliance.abac

default allow = false

# Global High-Risk Denial Directive (Risk Score >= 80)
deny {
    input.subject.risk_score >= 80
}

# Policy ID: FIN-001 (Finance Document Access)
allow {
    input.action == "Read"
    input.resource.department == "Finance"
    input.subject.clearance_rank >= 3
}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(regoCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const element = document.createElement("a");
    const file = new Blob([regoCode], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = "compliance_abac_bundle.rego";
    document.body.appendChild(element);
    element.click();
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
  };

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: CAP?.text }}>CNCF Open Policy Agent (OPA) Rego Generator</h3>
          <p style={{ margin: 0, fontSize: 13, color: CAP?.textDim }}>Linked Rego bundle export & deployment configs for K8s, Envoy Proxy & Istio</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={handleCopy} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 8, border: `1px solid ${CAP?.border}`, background: CAP?.panel, color: CAP?.text, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
            {copied ? <Check size={14} color="#5A7A6A" /> : <Copy size={14} />} {copied ? "Copied!" : "Copy Rego Code"}
          </button>
          <button onClick={handleDownload} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", borderRadius: 8, border: "none", background: CAP?.purple || "#C9A96E", color: "#16120E", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
            <Download size={14} /> Download OPA Bundle
          </button>
        </div>
      </div>

      <pre style={{ background: "#16120E", color: "#E6DACE", padding: 18, borderRadius: 10, fontSize: 12.5, lineHeight: 1.5, overflowX: "auto", margin: 0 }}>
        {regoCode}
      </pre>
    </div>
  );
}
