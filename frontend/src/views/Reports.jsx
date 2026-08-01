import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getScans } from "../api";
import { SeverityBadge } from "../components/Shared";

export default function Reports() {
  const [scans, setScans] = useState(null);
  useEffect(() => { getScans().then(setScans); }, []);
  if (!scans) return <div style={{ color: "var(--text-faint)", padding: 40 }}>Loading…</div>;

  return (
    <motion.div className="card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="card-title" style={{ marginBottom: 14 }}>Scan History</div>
      <table className="tbl">
        <thead>
          <tr><th>Document</th><th>Uploaded By</th><th>Score</th><th>Findings</th><th>Top Severity</th><th>Time</th></tr>
        </thead>
        <tbody>
          {scans.map((s) => {
            const top = s.violations[0]?.severity;
            const color = s.compliance_score >= 80 ? "var(--p4)" : s.compliance_score >= 60 ? "var(--p3)" : "var(--p1)";
            return (
              <tr key={s.scan_id}>
                <td style={{ fontWeight: 600 }}>{s.document_name}</td>
                <td style={{ color: "var(--text-dim)" }}>{s.uploaded_by}</td>
                <td><strong style={{ color }}>{s.compliance_score}%</strong></td>
                <td>{s.total_violations}</td>
                <td>{top ? <SeverityBadge sev={top} /> : <span style={{ color: "var(--p4)" }}>Clean</span>}</td>
                <td style={{ color: "var(--text-faint)", fontSize: 12.5 }}>
                  {new Date(s.created_at).toLocaleString()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </motion.div>
  );
}
