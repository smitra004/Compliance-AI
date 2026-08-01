
import { useEffect, useMemo, useState } from "react";
import { Play, Pause, RotateCcw } from "lucide-react";
import { formatRationale } from "../utils/formatRationale";

/**
 * AgentOrchestra — live multi-agent orchestration view.
 *
 * Renders the REAL per-agent council output for a scan
 * (`ScanRecord.agent_reports`, populated by
 * backend/app/pipeline/agents.py as
 * [{ agent, verdict, rationale }]) as an orbit + reasoning-trace replay.
 *
 * `agent_reports` is only populated when the scan ran the live LLM agent
 * council (i.e. `not config.DEMO_MODE`, a real API key configured) — in
 * demo mode, or when the scan fell back to the deterministic rule engine,
 * it's an empty list, and this component says so honestly instead of
 * fabricating a scripted narrative. The agent roster, count, and colors
 * are all derived from whatever agents are actually present in the data —
 * nothing about the agent names/order is hardcoded, since the real
 * council composition (GDPR/Security/Legal/Internal Policy today) is a
 * backend concern that can change independently of this component.
 *
 * Props:
 *   - title, scanId    : header text
 *   - agentReports     : ScanRecord.agent_reports — [{ agent, verdict, rationale }]
 *   - analysisMode     : ScanRecord.analysis_mode — shown in the empty state
 */

const PAL = {
  ivory: "#fbf9f7",
  ink: "#16120E",
  ink3: "#5C5248",
  ink4: "#8C8278",
  border: "rgba(22,18,14,0.10)",
  primary: "#C95A32",
  green: "#5A7A6A",
  amber: "#B98A2E",
  red: "#B85C38",
};

// Positional palette applied by index — a presentation detail, not a
// per-agent hardcoded fact, so it works for any agent name the backend
// ever reports.
const ORBIT_PALETTE = ["#C95A32", "#4C6B8A", "#5C8A5C", "#6E4F8A", "#B98A2E", "#8A5A44", "#2E2A26", "#A3522E"];

function VerdictPill({ verdict }) {
  const tone =
    verdict === "Concern raised" ? PAL.red :
    verdict === "Unavailable" ? PAL.ink4 :
    PAL.green;
  return (
    <span style={{
      fontSize: 10.5, fontWeight: 700, padding: "3px 9px", borderRadius: 99,
      background: `${tone}1F`, color: tone, border: `1px solid ${tone}40`,
    }}>
      {verdict}
    </span>
  );
}

function Orbit({ agents, activeId }) {
  const cx = 260, cy = 200, r = 150;
  return (
    <svg viewBox="0 0 520 400" style={{ width: "100%", height: "100%" }}>
      <defs>
        <radialGradient id="agentOrbitCore" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={PAL.primary} stopOpacity="0.45" />
          <stop offset="100%" stopColor={PAL.primary} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r={r + 30} fill="url(#agentOrbitCore)" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#EEE7E1" strokeDasharray="4 6" />
      <circle cx={cx} cy={cy} r={44} fill="#1c1815" />
      <text x={cx} y={cy - 4} textAnchor="middle" fill="#fff" fontSize="12" fontFamily="'Instrument Serif', Georgia, serif" fontStyle="italic">Council</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill={PAL.primary} fontSize="9" letterSpacing="1.5">ORCHESTRATOR</text>

      {agents.map((a, i) => {
        const angle = (i / Math.max(agents.length, 1)) * Math.PI * 2 - Math.PI / 2;
        const x = cx + Math.cos(angle) * r;
        const y = cy + Math.sin(angle) * r;
        const active = a.id === activeId;
        return (
          <g key={a.id}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke={active ? PAL.primary : "#E8E0D8"} strokeWidth={active ? 1.5 : 1} strokeDasharray={active ? "0" : "3 5"} />
            <circle cx={x} cy={y} r={active ? 22 : 16} fill={active ? a.color : "#fff"} stroke={a.color} strokeWidth={2} />
            {active && <circle cx={x} cy={y} r={30} fill="none" stroke={a.color} strokeOpacity="0.35" />}
            <text x={x} y={y + (y > cy ? 40 : -26)} textAnchor="middle" fontSize="11" fill={PAL.ink}>{a.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

export default function AgentOrchestra({
  title = "Live Multi-Agent Orchestration",
  scanId = "current scan",
  agentReports = [],
  analysisMode,
}) {
  const [running, setRunning] = useState(true);
  const [tick, setTick] = useState(0);

  const reports = Array.isArray(agentReports) ? agentReports : [];

  // Data-driven roster: one entry per distinct agent name actually
  // present in this scan's real council output, in first-seen order.
  const agents = useMemo(() => {
    const seen = new Map();
    reports.forEach((r) => {
      if (r?.agent && !seen.has(r.agent)) {
        seen.set(r.agent, { id: r.agent, name: r.agent, color: ORBIT_PALETTE[seen.size % ORBIT_PALETTE.length] });
      }
    });
    return [...seen.values()];
  }, [reports]);

  // Reset the replay whenever we're handed a different scan's reports.
  useEffect(() => {
    setTick(0);
    setRunning(reports.length > 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports]);

  useEffect(() => {
    if (!running) return;
    if (tick >= reports.length - 1) return;
    const id = setInterval(() => setTick((t) => Math.min(reports.length - 1, t + 1)), 900);
    return () => clearInterval(id);
  }, [running, tick, reports.length]);

  const visible = reports.slice(0, tick + 1);
  const currentAgent = visible[visible.length - 1]?.agent;
  const done = reports.length > 0 && tick >= reports.length - 1;

  function restart() {
    setTick(0);
    setRunning(true);
  }

  const header = (
    <div style={{ padding: "24px 28px 4px", display: "flex", alignItems: "start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
      <div>
        <div style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontStyle: "italic", fontSize: 26, color: PAL.ink, lineHeight: 1.1 }}>
          {title}
        </div>
        <div style={{ fontSize: 12.5, color: PAL.ink4, marginTop: 4, maxWidth: 560 }}>
          Per-agent verdicts from the actual compliance council that reviewed this document.
        </div>
      </div>
      {reports.length > 0 && (
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setRunning((r) => !r)}
            style={{
              display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 99,
              border: `1px solid ${PAL.border}`, background: "#fff", padding: "8px 16px",
              fontSize: 12.5, cursor: "pointer", color: PAL.ink,
            }}
          >
            {running ? <Pause size={13} /> : <Play size={13} />} {running ? "Pause" : "Resume"}
          </button>
          <button
            onClick={restart}
            style={{
              display: "inline-flex", alignItems: "center", gap: 6, borderRadius: 99,
              border: "none", background: PAL.primary, color: "#fff", padding: "8px 16px",
              fontSize: 12.5, fontWeight: 600, cursor: "pointer",
            }}
          >
            <RotateCcw size={13} /> Replay
          </button>
        </div>
      )}
    </div>
  );

  if (reports.length === 0) {
    return (
      <div style={{ background: PAL.ivory, border: `1px solid ${PAL.border}`, borderRadius: 18, overflow: "hidden", width: "100%", minWidth: 0, boxSizing: "border-box" }}>
        {header}
        <div style={{ padding: "20px 28px 32px", fontSize: 13, color: PAL.ink3, lineHeight: 1.6 }}>
          No per-agent council output was recorded for this scan
          {analysisMode ? ` (analysis mode: ${analysisMode})` : ""}. This happens when a scan
          runs on the deterministic rule engine rather than the live LLM agent council — the
          compliance findings themselves are still real, just not broken down by individual agent.
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: PAL.ivory, border: `1px solid ${PAL.border}`, borderRadius: 18, overflow: "hidden", width: "100%", minWidth: 0, boxSizing: "border-box" }}>
      {header}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 16, padding: 24, width: "100%", boxSizing: "border-box" }}>
        <div style={{ background: "#fff", border: `1px solid ${PAL.border}`, borderRadius: 14, padding: 20, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.10em", color: PAL.primary, fontWeight: 700 }}>
              Agent council
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: PAL.ink4 }}>
              <span style={{
                width: 7, height: 7, borderRadius: "50%", background: running ? PAL.green : PAL.ink4,
                boxShadow: running ? "0 0 0 3px rgba(90,122,106,0.18)" : "none",
              }} />
              {running ? "replaying" : "paused"}
            </div>
          </div>
          <div style={{ marginTop: 20, height: 300 }}>
            <Orbit agents={agents} activeId={currentAgent} />
          </div>
          <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: `repeat(${Math.min(agents.length, 4)}, minmax(0, 1fr))`, gap: 8 }}>
            {agents.map((a) => {
              const active = currentAgent === a.id;
              const lastForAgent = [...visible].reverse().find((r) => r.agent === a.id);
              return (
                <div
                  key={a.id}
                  style={{
                    borderRadius: 10, padding: "8px 10px", fontSize: 11,
                    border: `1px solid ${active ? PAL.primary : PAL.border}`,
                    background: active ? `${PAL.primary}0D` : "#fff",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: a.color, flexShrink: 0 }} />
                    <span style={{ fontWeight: 600, color: PAL.ink }}>{a.name}</span>
                  </div>
                  <div style={{ marginTop: 3, fontSize: 10, color: PAL.ink4, lineHeight: 1.25 }}>
                    {lastForAgent ? lastForAgent.verdict : "Pending…"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ background: "#fff", border: `1px solid ${PAL.border}`, borderRadius: 14, padding: 20, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.10em", color: PAL.primary, fontWeight: 700 }}>
            Reasoning trace
          </div>
          <div style={{ marginTop: 4, fontFamily: "'Instrument Serif', Georgia, serif", fontStyle: "italic", fontSize: 19, color: PAL.ink }}>
            Chain of thought · {scanId}
          </div>
          <div style={{ marginTop: 14, flex: 1, overflowY: "auto", maxHeight: 420, display: "flex", flexDirection: "column", gap: 10, paddingRight: 4 }}>
            {visible.map((v, i) => {
              const agent = agents.find((a) => a.id === v.agent);
              return (
                <div
                  key={i}
                  style={{
                    borderRadius: 12, border: `1px solid ${PAL.border}`, background: "rgba(237,231,218,0.35)",
                    padding: 14, animation: "twinFadeIn 0.25s ease both",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 11.5 }}>
                      <span style={{ width: 7, height: 7, borderRadius: "50%", background: agent?.color }} />
                      <span style={{ fontWeight: 600, color: PAL.ink }}>{agent?.name || v.agent}</span>
                      <span style={{ color: PAL.ink4 }}>· step {i + 1}</span>
                    </div>
                    <VerdictPill verdict={v.verdict} />
                  </div>
                  <p style={{ marginTop: 8, marginBottom: 0, fontSize: 13, color: PAL.ink, lineHeight: 1.5 }}>{formatRationale(v.rationale)}</p>
                </div>
              );
            })}
            {done && (
              <div style={{ borderRadius: 12, border: `1px solid ${PAL.primary}60`, background: `${PAL.primary}0D`, padding: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{
                    fontSize: 10.5, fontWeight: 700, padding: "3px 9px", borderRadius: 99,
                    background: `${PAL.primary}1F`, color: PAL.primary,
                  }}>
                    Complete
                  </span>
                  <span style={{ fontSize: 12, color: PAL.ink3 }}>
                    {reports.length} agent{reports.length === 1 ? "" : "s"} reported ·{" "}
                    {reports.filter((r) => r.verdict === "Concern raised").length} raised a concern
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes twinFadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}
