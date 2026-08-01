import React, { useState } from "react";
import { Lock, FileText, CheckCircle2, Shield } from "lucide-react";

export default function DataMaskingEngine({ CAP, rawContent, maskedContent, obligations }) {
  const [testText, setTestText] = useState("User PAN card is ABCDE1234F and Aadhaar is 2345 6789 0123. Email: exec@corp.com");
  const [testResult, setTestResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runMasking = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/abac/enforce-masking", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: testText,
          obligations: ["Mask PAN", "Mask Aadhaar", "Hide Email"],
        }),
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      console.error("Masking error:", err);
    } finally {
      setLoading(false);
    }
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
    label: {
      fontSize: 12,
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: CAP?.textDim || "#5C5248",
      marginBottom: 4,
      display: "block",
    },
  };

  return (
    <div style={styles.card}>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 0, marginBottom: 14, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
        <Lock size={18} color={CAP?.purple} /> Real Field-Level Data Masking & Obligations Engine
      </h3>

      {/* Side-by-side Original vs Masked Diff View */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <label style={styles.label}>1. Raw Document Content Input (Unmasked)</label>
          <pre style={{ background: "#16120E", color: "#E6DACE", padding: 14, borderRadius: 8, fontSize: 12, height: 140, overflowY: "auto", margin: 0 }}>
            {rawContent || testText}
          </pre>
        </div>

        <div>
          <label style={styles.label}>2. Field-Level Redacted Output (Applied Obligations)</label>
          <pre style={{ background: "#16120E", color: "#5A7A6A", padding: 14, borderRadius: 8, fontSize: 12, height: 140, overflowY: "auto", margin: 0 }}>
            {maskedContent || testResult?.masked_text || "Execute masking..."}
          </pre>
        </div>
      </div>

      {/* Applied Redaction Highlights & Restriction Flags */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: CAP?.textDim }}>Redaction Highlights:</span>
        {["PAN Redacted", "Aadhaar Redacted", "Email Redacted", "Download Disabled", "Export Disabled"].map((badge, idx) => (
          <span key={idx} style={{ padding: "4px 10px", borderRadius: 12, background: "rgba(201, 169, 110, 0.15)", color: CAP?.purple || "#C9A96E", border: `1px solid ${CAP?.purple || "#C9A96E"}`, fontSize: 11, fontWeight: 700 }}>
            🔒 {badge}
          </span>
        ))}
      </div>
    </div>
  );
}
