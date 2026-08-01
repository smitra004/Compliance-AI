import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import { FileSearch, AlertTriangle, FileCheck2, ShieldAlert, Lock, Database, FileText, Settings } from "lucide-react";
import { getDashboard } from "../api";
import { ScoreRing, StatCard } from "../components/Shared";

const CAT_COLORS = ["#38BDF8", "#8B5CF6", "#22D3EE", "#A78BFA", "#5C6B8F"];
const AREA_ICONS = { "Access Control": <Lock size={16} />, "Data Protection": <Database size={16} />,
  "Policy Violation": <FileText size={16} />, "Configuration": <Settings size={16} /> };

export default function Dashboard() {
  const [d, setD] = useState(null);
  useEffect(() => { getDashboard().then(setD); }, []);
  if (!d) return <Loading />;

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="grid stat-grid" style={{ marginBottom: 18 }}>
        <StatCard icon={<FileSearch size={20} />} value={d.policies_scanned.toLocaleString()}
          label="Policies Scanned" delta="12.5%" deltaDir="up" accent="#38BDF8" />
        <StatCard icon={<AlertTriangle size={20} />} value={d.risks_detected}
          label="Risks Detected" delta="active" deltaDir="down" accent="#F4524D" />
        <StatCard icon={<FileCheck2 size={20} />} value={d.documents_analyzed.toLocaleString()}
          label="Documents Analyzed" delta="9.4%" deltaDir="up" accent="#34D399" />
        <StatCard icon={<ShieldAlert size={20} />} value={`${d.overall_compliance_score}%`}
          label="Avg Compliance Score" accent="#8B5CF6" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1.1fr 1fr 1fr", marginBottom: 18 }}>
        <div className="card">
          <div className="card-title">Compliance Trend · 30 days</div>
          <ResponsiveContainer width="100%" height={210}>
            <AreaChart data={d.compliance_trend} margin={{ top: 16, right: 6, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="label" stroke="#5C6B8F" fontSize={11} tickLine={false} />
              <YAxis stroke="#5C6B8F" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
              <Tooltip
                contentStyle={tip}
                labelFormatter={(label) => label}
                formatter={(value) => [`${value}%`, "Compliance Score"]}
              />
              <Area type="monotone" dataKey="value" name="Compliance Score" stroke="#38BDF8" strokeWidth={2.5} fill="url(#g1)" dot={{ r: 3, fill: "#38BDF8", strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title">Overall Compliance</div>
          <div style={{ display: "grid", placeItems: "center", height: 210 }}>
            <ScoreRing score={d.overall_compliance_score} />
          </div>
        </div>

        <div className="card">
          <div className="card-title">Risk by Category</div>
          <div style={{ display: "flex", alignItems: "center", height: 210 }}>
            <ResponsiveContainer width="55%" height={180}>
              <PieChart>
                <Pie data={d.risk_by_category} dataKey="value" nameKey="name"
                  innerRadius={42} outerRadius={70} paddingAngle={3} stroke="none">
                  {d.risk_by_category.map((_, i) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tip} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1, fontSize: 12.5 }}>
              {d.risk_by_category.map((c, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
                  <span className="dot" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }} />
                  <span style={{ color: "var(--text-dim)", flex: 1 }}>{c.name}</span>
                  <strong>{c.value}%</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr" }}>
        <div className="card">
          <div className="card-title">Top Risky Areas</div>
          <div className="grid" style={{ gridTemplateColumns: "repeat(2,1fr)", marginTop: 12 }}>
            {d.top_risky_areas.map((a, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0" }}>
                <div className="icon-chip" style={{ color: "var(--cyan)", background: "rgba(56,189,248,0.1)" }}>
                  {AREA_ICONS[a.name] || <ShieldAlert size={16} />}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{a.name}</div>
                  <div style={{ color: "var(--p2)", fontSize: 12.5 }}>{a.risks} risks</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Recent Alerts</div>
          <div style={{ marginTop: 6 }}>
            {d.recent_alerts.length === 0 && <p style={{ color: "var(--text-faint)", fontSize: 13 }}>No alerts.</p>}
            {d.recent_alerts.map((a, i) => (
              <div key={i} className="alert-row">
                <span className="dot" style={{ background: a.severity === "Critical" ? "var(--p1)" : a.severity === "High" ? "var(--p2)" : "var(--p3)" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{a.title}</div>
                  <div style={{ fontSize: 11.5, color: "var(--text-faint)" }}>{a.document}</div>
                </div>
                <span style={{ fontSize: 11.5, color: "var(--text-dim)" }}>{a.severity}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

const tip = { background: "#0E1528", border: "1px solid rgba(56,189,248,0.3)", borderRadius: 10, fontSize: 12 };

function Loading() {
  return <div style={{ color: "var(--text-faint)", padding: 40 }}>Loading dashboard…</div>;
}
