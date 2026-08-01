import { motion } from "framer-motion";
import { ShieldCheck, FileWarning, Quote } from "lucide-react";
import { SEV, REG_LABEL } from "../api";

export function ScoreRing({
  score,
  highCount = 0,
  criticalCount = 0,
  size = 150
}) {
  const r = size / 2 - 11;
  const c = 2 * Math.PI * r;

  let color;
  if (score >= 80) {
    color = "var(--p4)";
  } else if (score >= 60) {
    color = "var(--p3)";
  } else {
    color = "var(--p1)";
  }

  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(80,120,200,0.15)"
          strokeWidth="11"
        />

        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={c}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          initial={{ strokeDashoffset: c }}
          animate={{
            strokeDashoffset: c - (c * score) / 100
          }}
          transition={{
            duration: 1.1,
            ease: "easeOut"
          }}
          style={{
            filter: `drop-shadow(0 0 8px ${color})`
          }}
        />
      </svg>

      <div className="score-num">
        <div
          style={{
            fontSize: size * 0.27,
            fontWeight: 700,
            color
          }}
        >
          {score}%
        </div>
      </div>
    </div>
  );
}

export function SeverityBadge({ sev }) {
  const s = SEV[sev];
  return (
    <span className="sev-badge"
      style={{ background: `${s.color}22`, color: s.color, border: `1px solid ${s.color}55` }}>
      {sev} · {s.label}
    </span>
  );
}

export function ViolationCard({ v, index }) {
  const color = SEV[v.severity].color;
  return (
    <motion.div className="viol" style={{ borderLeftColor: color }}
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index, duration: 0.35 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ display: "flex", gap: 11, alignItems: "center" }}>
          <FileWarning size={18} color={color} />
          <strong style={{ fontSize: 15 }}>{v.title}</strong>
        </div>
        <SeverityBadge sev={v.severity} />
      </div>
      <div className="excerpt">{v.excerpt}</div>
      <p style={{ fontSize: 13.5, color: "var(--text-dim)", lineHeight: 1.55 }}>{v.explanation}</p>
      <p style={{ fontSize: 13, marginTop: 8 }}>
        <span style={{ color: "var(--p4)", fontWeight: 700 }}>→ Fix: </span>
        <span style={{ color: "var(--text-dim)" }}>{v.recommendation}</span>
      </p>
      {v.citation && (
        <div className="citation">
          <Quote size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            <strong>{v.citation.clause}</strong>
            <span style={{ color: "var(--text-faint)" }}> · {REG_LABEL[v.citation.regulation]} · match {(v.citation.similarity * 100).toFixed(0)}%</span>
            <div style={{ color: "var(--text-faint)", marginTop: 3, fontStyle: "italic" }}>
              "{v.citation.text}"
            </div>
          </span>
        </div>
      )}
    </motion.div>
  );
}

export function StatCard({ icon, value, label, delta, deltaDir, accent }) {
  return (
    <motion.div className="card" initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div className="icon-chip" style={{ color: accent, background: `${accent}18` }}>{icon}</div>
        {delta && <span className={`delta ${deltaDir}`}>{deltaDir === "up" ? "▲" : "▼"} {delta}</span>}
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </motion.div>
  );
}
