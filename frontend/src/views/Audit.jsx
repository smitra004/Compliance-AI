import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getAudit } from "../api";

const ACTION_COLOR = {
  UPLOAD_AND_SCAN: "var(--cyan)", LOGIN: "var(--p4)",
  POLICY_LOAD: "var(--purple)",
};

export default function Audit() {
  const [rows, setRows] = useState(null);
  useEffect(() => { getAudit().then(setRows); }, []);
  if (!rows) return <div style={{ color: "var(--text-faint)", padding: 40 }}>Loading…</div>;

  return (
    <motion.div className="card" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="card-title" style={{ marginBottom: 6 }}>Immutable Audit Trail</div>
      <p style={{ color: "var(--text-faint)", fontSize: 12.5, marginBottom: 16 }}>
        Every upload, scan, and policy action is logged for auditor traceability.
      </p>
      <table className="tbl">
        <thead>
          <tr><th>Time</th><th>Actor</th><th>Role</th><th>Action</th><th>Target</th><th>Detail</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td style={{ color: "var(--text-faint)", fontSize: 12.5, whiteSpace: "nowrap" }}>
                {new Date(r.timestamp).toLocaleString()}
              </td>
              <td style={{ color: "var(--text-dim)" }}>{r.actor}</td>
              <td><span className="tag" style={{ background: "rgba(139,92,246,0.14)", color: "var(--violet)" }}>{r.role}</span></td>
              <td><span style={{ color: ACTION_COLOR[r.action] || "var(--text)", fontWeight: 700, fontSize: 12.5 }}>{r.action}</span></td>
              <td>{r.target}</td>
              <td style={{ color: "var(--text-dim)", fontSize: 12.5 }}>{r.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  );
}
