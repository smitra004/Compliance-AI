import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Info,
  Zap,
  ShieldAlert,
  CalendarClock,
  BrainCircuit,
  Scale,
  Users,
  Eye,
  FileText,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  X,
} from "lucide-react";
import {
  getDashboardMetrics,
  getDashboardNarrative,
  getDashboardCapabilities,
  getCopilotSuggestions,
  getCopilotExamples,
  askCopilot,
} from "./api";

const PALETTE = {
  midnight: "#0A1633", // Deep Midnight Navy
  royalBlue: "#1B5BFF", // Royal Governance Blue
  gold: "#D4AF37", // Intelligent Gold
  ivory: "#FAF2E8", // Warm Ivory
  frosted: "rgba(255,255,255,0.72)", // Soft Frosted White
  frostedSolid: "#FFFFFF",
};

const CAP = {
  bg: PALETTE.ivory,
  bgGradient:
    "radial-gradient(1200px 720px at 12% -12%, rgba(212,175,55,0.18) 0%, rgba(250,242,232,1) 60%), radial-gradient(900px 650px at 105% 10%, rgba(27,91,255,0.18) 0%, rgba(250,242,232,0) 45%), radial-gradient(700px 700px at 78% 108%, rgba(10,22,51,0.10) 0%, rgba(250,242,232,0) 58%)",
  panel: "rgba(255,255,255,0.60)",
  panel2: "rgba(255,255,255,0.42)",
  border: "rgba(10,22,51,0.14)",
  border2: "rgba(27,91,255,0.22)",
  text: "#0B1324",
  textDim: "rgba(11,19,36,0.70)",
  textFaint: "rgba(11,19,36,0.48)",
  navy: PALETTE.midnight,
  blue: PALETTE.royalBlue,
  gold: PALETTE.gold,
  shadow: "0 26px 70px -32px rgba(10,22,51,0.25)",
};

function useReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(!!mq.matches);
    onChange();
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);
  return reduced;
}

function InjectGovernanceStyles() {
  useEffect(() => {
    const css = `
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500&family=Outfit:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root{
  --gov-navy:${CAP.navy};
  --gov-blue:${CAP.blue};
  --gov-gold:${CAP.gold};
  --gov-ivory:${CAP.bg};
}

*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  font-family: Manrope, system-ui, sans-serif;
  background:${CAP.bg};
  color:${CAP.text};
  overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background:${CAP.bgGradient};
}

h1,h2,h3{font-family: Fraunces, serif; letter-spacing:-0.02em}

::selection{background:rgba(212,175,55,0.25)}

.gov-surface{
  background: ${CAP.panel};
  border: 1px solid ${CAP.border};
  border-radius: 22px;
  box-shadow: ${CAP.shadow};
  backdrop-filter: blur(18px);
}

.gov-soft{
  background: rgba(255,255,255,0.52);
  border: 1px solid rgba(10,22,51,0.10);
  border-radius: 18px;
  backdrop-filter: blur(14px);
}

.gov-aurora{
  background: linear-gradient(135deg, rgba(27,91,255,0.20), rgba(212,175,55,0.20));
}

.gov-glass-line{
  background: linear-gradient(90deg, rgba(212,175,55,0.55), rgba(27,91,255,0.45));
  height:1px; opacity:0.55;
}

.gov-btn{
  border: 1px solid rgba(10,22,51,0.14);
  background: rgba(255,255,255,0.55);
  color: ${CAP.text};
  border-radius: 14px;
  padding: 10px 14px;
  font-weight: 800;
  cursor: pointer;
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}
.gov-btn:hover{transform: translateY(-1px); border-color: rgba(27,91,255,0.35); background: rgba(255,255,255,0.70)}
.gov-btn:active{transform: translateY(0px)}
.gov-btn.primary{
  border:none;
  color: #081024;
  background: linear-gradient(135deg, rgba(212,175,55,0.90), rgba(27,91,255,0.80));
  box-shadow: 0 18px 44px -18px rgba(27,91,255,0.35);
}

.gov-chip{
  display:inline-flex; align-items:center; gap:8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(10,22,51,0.12);
  background: rgba(255,255,255,0.56);
  color: ${CAP.textDim};
  font-weight: 800;
  font-size: 12px;
}

.gov-h1{font-size: 56px; line-height: 1.0;}
.gov-h2{font-size: 28px; line-height:1.1; font-weight:800}

@media (max-width: 900px){
  .gov-h1{font-size: 40px}
}

.gov-kbd{
  font-family: ui-monospace, JetBrains Mono, SF Mono, monospace;
  font-weight:800;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 10px;
  border: 1px solid rgba(10,22,51,0.14);
  background: rgba(255,255,255,0.55);
}

.gov-scrollhint{
  display:flex; align-items:center; gap:10px;
  color:${CAP.textDim}; font-weight:800;
  font-size: 12px;
}

.gov-fineprint{color:${CAP.textFaint}; font-size:12.5px; line-height:1.6}

.gov-fade-in{opacity:0; transform: translateY(10px)}

@media (prefers-reduced-motion: no-preference){
  .gov-fade-in[data-inview="true"]{
    animation: govFadeIn .7s cubic-bezier(.16,1,.3,1) both;
  }
  @keyframes govFadeIn{
    from{opacity:0; transform: translateY(12px)}
    to{opacity:1; transform: translateY(0)}
  }
}

.gov-copilot-input{
  width:100%;
  border-radius: 18px;
  padding: 14px 16px;
  border: 1px solid rgba(10,22,51,0.14);
  background: rgba(255,255,255,0.58);
  outline: none;
  color:${CAP.text};
  font-weight:700;
  font-size: 14px;
}

.gov-copilot-input:focus{
  border-color: rgba(27,91,255,0.45);
  box-shadow: 0 0 0 5px rgba(27,91,255,0.12);
}

.gov-card{
  border-radius: 22px;
  background: rgba(255,255,255,0.60);
  border: 1px solid rgba(10,22,51,0.12);
  padding: 16px 16px;
  box-shadow: ${CAP.shadow};
  backdrop-filter: blur(18px);
}

.gov-cardTitle{display:flex; align-items:center; gap:10px; font-weight:950}
.gov-cardTitle b{font-size:14px}
.gov-cardBody{color:${CAP.textDim}; margin-top: 10px; font-size: 13.5px; line-height: 1.55}
.gov-cardMeta{margin-top: 12px; display:flex; flex-wrap:wrap; gap:10px}
.gov-tag{font-weight:900; font-size: 12px; padding: 6px 10px; border-radius: 999px; border: 1px solid rgba(10,22,51,0.12); background: rgba(255,255,255,0.45);}
.gov-tag.blue{border-color: rgba(27,91,255,0.35); color: rgba(27,91,255,0.95);}
.gov-tag.gold{border-color: rgba(212,175,55,0.40); color: rgba(154,122,19,1);}

.gov-tile{
  border-radius: 24px;
  padding: 18px;
  border: 1px solid rgba(10,22,51,0.12);
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(18px);
  box-shadow: ${CAP.shadow};
  position: relative;
  overflow:hidden;
}
.gov-tile::after{
  content:''; position:absolute; inset:-1px;
  background: radial-gradient(420px 240px at 30% 0%, rgba(27,91,255,0.18), transparent 55%), radial-gradient(420px 240px at 70% 100%, rgba(212,175,55,0.16), transparent 60%);
  pointer-events:none;
}
.gov-tile > *{position: relative; z-index: 1;}

.gov-ring{
  width: 92px; height: 92px;
  border-radius: 999px;
  display:grid;
  place-items:center;
  background: rgba(255,255,255,0.40);
  border: 1px solid rgba(10,22,51,0.10);
}

.gov-ring svg{display:block}
.gov-ring .label{font-size: 13px; font-weight: 950}
.gov-ring .sub{font-size: 11px; font-weight: 900; color:${CAP.textFaint}; letter-spacing:0.08em; text-transform: uppercase; margin-top:2px}

.gov-nodeBg{
  filter: drop-shadow(0 20px 40px rgba(10,22,51,0.20));
}

.gov-mutedLink{color:${CAP.textDim}; font-weight:900; text-decoration:none}
.gov-mutedLink:hover{color:${CAP.text}; text-decoration:underline}

.gov-timelineLine{
  height:1px;
  background: linear-gradient(90deg, rgba(27,91,255,0.4), rgba(212,175,55,0.25));
}

`;
    const s = document.createElement("style");
    s.textContent = css;
    document.head.prepend(s);
    return () => s.remove();
  }, []);
  return null;
}

function AuroraNetwork({ reduced }) {
  // Lightweight canvas-like effect via absolutely-positioned nodes.
  const nodes = useMemo(
    () =>
      new Array(18).fill(0).map((_, i) => {
        const x = 10 + Math.round((i % 6) * 16 + (i % 2 ? 3 : -3));
        const y = 18 + Math.round(Math.floor(i / 6) * 22 + (i % 3 ? 4 : -2));
        const size = 12 + (i % 5) * 3;
        const delay = (i % 7) * 120;
        const alpha = 0.55 + (i % 4) * 0.10;
        const hue = i % 2 === 0 ? "blue" : "gold";
        return { id: i, x, y, size, delay, alpha, hue };
      }),
    []
  );

  return (
    <div
      aria-hidden
      className="gov-nodeBg"
      style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}
    >
      {/* Ambient lines */}
      <div
        style={{
          position: "absolute",
          inset: -40,
          background:
            "radial-gradient(900px 500px at 30% 0%, rgba(27,91,255,0.18), transparent 55%), radial-gradient(650px 400px at 80% 100%, rgba(212,175,55,0.14), transparent 60%)",
        }}
      />

      {/* Node lattice */}
      {nodes.map((n) => {
        const color = n.hue === "blue" ? "rgba(27,91,255,0.85)" : "rgba(212,175,55,0.90)";
        const ring = n.hue === "blue" ? "rgba(27,91,255,0.20)" : "rgba(212,175,55,0.18)";
        return (
          <motion.div
            key={n.id}
            initial={{ opacity: 0.2, scale: 0.9 }}
            animate={reduced ? { opacity: n.alpha, scale: 1 } : { opacity: n.alpha, scale: [0.95, 1.05, 1] }}
            transition={{ duration: 1.9, delay: n.delay / 1000, repeat: reduced ? 0 : Infinity, repeatType: "mirror" }}
            style={{
              position: "absolute",
              left: `${n.x}%`,
              top: `${n.y}%`,
              width: n.size,
              height: n.size,
              borderRadius: 999,
              background: color,
              boxShadow: `0 0 0 1px rgba(255,255,255,0.22), 0 0 26px ${ring}`,
              backdropFilter: "blur(6px)",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: -8,
                borderRadius: 999,
                border: `1px solid ${ring}`,
                opacity: 0.65,
              }}
            />
          </motion.div>
        );
      })}

      {/* Connection glow */}
      <svg
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        {new Array(12).fill(0).map((_, i) => {
          const a = nodes[i * 1]?.id ?? i;
          const b = nodes[(i * 1 + 7) % nodes.length]?.id ?? i;
          const na = nodes[a % nodes.length];
          const nb = nodes[b % nodes.length];
          if (!na || !nb) return null;
          const x1 = na.x;
          const y1 = na.y;
          const x2 = nb.x;
          const y2 = nb.y;
          const stroke = i % 2 === 0 ? "rgba(27,91,255,0.20)" : "rgba(212,175,55,0.18)";
          return (
            <path
              key={i}
              d={`M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1 - 8}, ${(x1 + x2) / 2} ${y2 + 8}, ${x2} ${y2}`}
              fill="none"
              stroke={stroke}
              strokeWidth={0.6}
              strokeDasharray={reduced ? undefined : "2 2"}
              opacity={0.8}
            />
          );
        })}
      </svg>
    </div>
  );
}

function GovernanceRing({ value, label, sublabel }) {
  const v = Math.max(0, Math.min(100, value));
  const stroke = v >= 85 ? "rgba(59,142,47,0.92)" : v >= 60 ? "rgba(212,175,55,0.95)" : "rgba(225,69,60,0.92)";
  const bg = "rgba(10,22,51,0.10)";
  const r = 38;
  const c = 2 * Math.PI * r;
  const dashOffset = c - (c * v) / 100;
  return (
    <div className="gov-ring">
      <svg width={88} height={88} viewBox="0 0 88 88" aria-hidden>
        <circle cx="44" cy="44" r={r} stroke={bg} strokeWidth="9" fill="none" />
        <circle
          cx="44"
          cy="44"
          r={r}
          stroke={stroke}
          strokeWidth="9"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={dashOffset}
          transform="rotate(-90 44 44)"
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.16,1,.3,1)" }}
        />
      </svg>
      <div style={{ position: "absolute", textAlign: "center" }}>
        <div className="label">{Math.round(v)}%</div>
        <div className="sub">{label}</div>
        {sublabel ? <div style={{ fontSize: 11, fontWeight: 950, color: "rgba(11,19,36,0.55)", marginTop: 2 }}>{sublabel}</div> : null}
      </div>
    </div>
  );
}

function GovernanceTile({ title, value, label, status, message, signalLevel, icon, accent = "blue" }) {
  const ringValue = value ?? 0;
  const ringLabel = label;
  return (
    <motion.div
      className="gov-tile"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      whileHover={{ y: -3 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div className="gov-cardTitle" style={{ fontSize: 13 }}>
            <span
              style={{
                width: 38,
                height: 38,
                borderRadius: 14,
                display: "grid",
                placeItems: "center",
                border: `1px solid rgba(10,22,51,0.12)`,
                background:
                  accent === "gold"
                    ? "rgba(212,175,55,0.14)"
                    : "rgba(27,91,255,0.12)",
                color: accent === "gold" ? "rgba(154,122,19,1)" : "rgba(27,91,255,1)",
              }}
            >
              {icon}
            </span>
            <b>{title}</b>
          </div>
          <div className="gov-fineprint" style={{ marginTop: 10 }}>
            {message || status || "Loading governance signals..."}
          </div>
        </div>
        <GovernanceRing value={ringValue} label={ringLabel} />
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="gov-glass-line" />
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, fontWeight: 900, color: "rgba(11,19,36,0.55)" }}>
            SIGNAL STRENGTH
          </div>
          <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, fontWeight: 950, color: accent === "gold" ? "rgba(154,122,19,1)" : "rgba(27,91,255,1)" }}>
            {signalLevel || "UNKNOWN"}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function BoardroomNarrative({ activeNarrative, narratives }) {
  const fallback = {
    executive: {
      eyebrow: "BOARDROOM MODE",
      title: "Governance Intelligence, in one breath.",
      body:
        "Boardroom Mode compresses the noise. You get the story, the risks, and the decisions still waiting for you—without the dashboard theatrics.",
    },
    audit: {
      eyebrow: "AUDIT PRESENTATION",
      title: "Readiness you can defend.",
      body:
        "Audit Presentation Mode emphasizes evidence alignment, control gaps, and the exact next steps required to close vulnerabilities.",
    },
  };
  const c = narratives?.[activeNarrative] ?? fallback[activeNarrative] ?? fallback.executive;
  return (
    <div className="gov-surface" style={{ padding: 18, marginBottom: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 14, alignItems: "flex-start" }}>
        <div>
          <div className="gov-chip" style={{ borderColor: "rgba(212,175,55,0.42)", color: "rgba(154,122,19,1)", background: "rgba(255,255,255,0.44)" }}>
            <Sparkles size={14} /> {c.eyebrow}
          </div>
          <h2 className="gov-h2" style={{ marginTop: 10 }}>
            {c.title}
          </h2>
          <p className="gov-fineprint" style={{ marginTop: 10, maxWidth: 740 }}>
            {c.body}
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <button className="gov-btn" onClick={() => document.getElementById("copilot")?.scrollIntoView({ behavior: "smooth" })}>
            Review Copilot
          </button>
          <button
            className="gov-btn primary"
            onClick={() => document.getElementById("command")?.scrollIntoView({ behavior: "smooth" })}
          >
            Board Command Center <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function GovernanceCard({ card }) {
  return (
    <motion.div
      className="gov-card"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div className="gov-cardTitle">
        <span
          style={{
            width: 34,
            height: 34,
            borderRadius: 14,
            display: "grid",
            placeItems: "center",
            background: card.accent === "gold" ? "rgba(212,175,55,0.15)" : "rgba(27,91,255,0.12)",
            border: "1px solid rgba(10,22,51,0.12)",
            color: card.accent === "gold" ? "rgba(154,122,19,1)" : "rgba(27,91,255,1)",
          }}
        >
          {card.icon}
        </span>
        <b>{card.title}</b>
      </div>
      <div className="gov-cardBody">{card.body}</div>
      {card.actions?.length ? (
        <div className="gov-cardMeta">
          {card.actions.map((a, idx) => (
            <span key={idx} className={`gov-tag ${a.kind}`}>
              {a.label}
            </span>
          ))}
        </div>
      ) : null}
      {card.footnote ? <div className="gov-fineprint" style={{ marginTop: 12 }}>{card.footnote}</div> : null}
    </motion.div>
  );
}

export default function AppGovernanceOS() {
  const reduced = useReducedMotion();
  const [boardMode, setBoardMode] = useState(false);
  const [boardNarrative, setBoardNarrative] = useState("executive");

  const [copilotPrompt, setCopilotPrompt] = useState("");
  const [cards, setCards] = useState([]);
  const [sending, setSending] = useState(false);
  const [lastPrompt, setLastPrompt] = useState(null);

  const [activeTiles, setActiveTiles] = useState(null);
  const [narratives, setNarratives] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [placeholderExample, setPlaceholderExample] = useState("e.g. Review nomination fit for a CFO successor...");
  const [capabilities, setCapabilities] = useState([]);

  const copilotRef = useRef(null);

  const fetchGovernanceMetrics = async () => {
    try {
      const response = await getDashboardMetrics();
      setActiveTiles(response);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDashboardData = async () => {
    try {
      const [metrics, narrative, suggestionList, exampleResponse, capabilityResponse] = await Promise.all([
        getDashboardMetrics(),
        getDashboardNarrative(),
        getCopilotSuggestions(),
        getCopilotExamples(),
        getDashboardCapabilities(),
      ]);

      setActiveTiles(metrics);
      setNarratives(narrative);
      setSuggestions(suggestionList || []);
      setPlaceholderExample(exampleResponse?.example || "e.g. Review nomination fit for a CFO successor...");
      setCapabilities(capabilityResponse?.availableCapabilities || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchGovernanceMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  const tiles = useMemo(
    () => [
      {
        key: "complianceHealth",
        title: "Compliance Health",
        value: activeTiles?.complianceHealth?.value,
        status: activeTiles?.complianceHealth?.status,
        message: activeTiles?.complianceHealth?.message,
        signalLevel: activeTiles?.complianceHealth?.signalLevel,
        label: "HEALTH",
        icon: <ShieldCheck size={16} />,
        accent: "blue",
      },
      {
        key: "policyAdoption",
        title: "Policy Adoption",
        value: activeTiles?.policyAdoption?.value,
        status: activeTiles?.policyAdoption?.status,
        message: activeTiles?.policyAdoption?.message,
        signalLevel: activeTiles?.policyAdoption?.signalLevel,
        label: "ADOPTION",
        icon: <FileText size={16} />,
        accent: "gold",
      },
      {
        key: "auditReadiness",
        title: "Audit Readiness",
        value: activeTiles?.auditReadiness?.value,
        status: activeTiles?.auditReadiness?.status,
        message: activeTiles?.auditReadiness?.message,
        signalLevel: activeTiles?.auditReadiness?.signalLevel,
        label: "READINESS",
        icon: <ShieldAlert size={16} />,
        accent: "blue",
      },
      {
        key: "approvalBottlenecks",
        title: "Approval Bottlenecks",
        value: activeTiles?.approvalBottlenecks?.value,
        status: activeTiles?.approvalBottlenecks?.status,
        message: activeTiles?.approvalBottlenecks?.message,
        signalLevel: activeTiles?.approvalBottlenecks?.signalLevel,
        label: "FLOW",
        icon: <Zap size={16} />,
        accent: "gold",
      },
      {
        key: "riskExposure",
        title: "Risk Exposure",
        value: activeTiles?.riskExposure?.value,
        status: activeTiles?.riskExposure?.status,
        message: activeTiles?.riskExposure?.message,
        signalLevel: activeTiles?.riskExposure?.signalLevel,
        label: "EXPOSURE",
        icon: <Scale size={16} />,
        accent: "blue",
      },
      {
        key: "nominationProgress",
        title: "Nomination Progress",
        value: activeTiles?.nominationProgress?.value,
        status: activeTiles?.nominationProgress?.status,
        message: activeTiles?.nominationProgress?.message,
        signalLevel: activeTiles?.nominationProgress?.signalLevel,
        label: "MOTION",
        icon: <Users size={16} />,
        accent: "gold",
      },
    ],
    [activeTiles]
  );

  function scrollToCopilot() {
    document.getElementById("copilot")?.scrollIntoView({ behavior: "smooth" });
  }

  async function onGovern() {
    const q = copilotPrompt.trim();
    if (!q) return;

    setSending(true);
    setLastPrompt(q);

    try {
      const response = await askCopilot(q);
      setCards(response.cards || []);
      await fetchGovernanceMetrics();
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
    }
  }

  // scroll reveal (no dependency)
  useEffect(() => {
    const els = Array.from(document.querySelectorAll(".gov-fade-in"));
    if (!els.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) (e.target).setAttribute("data-inview", "true");
        }
      },
      { threshold: 0.12 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [boardMode]);

  return (
    <>
      <InjectGovernanceStyles />

      <div style={{ minHeight: "100vh", position: "relative" }}>
        {/* Top thin authority bar */}
        <div
          style={{
            position: "sticky",
            top: 0,
            zIndex: 50,
            background: "rgba(250,242,232,0.70)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid rgba(10,22,51,0.10)",
          }}
        >
          <div
            style={{
              maxWidth: 1400,
              margin: "0 auto",
              padding: "14px 22px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 14,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 14,
                  display: "grid",
                  placeItems: "center",
                  background: "linear-gradient(135deg, rgba(27,91,255,0.25), rgba(212,175,55,0.28))",
                  border: "1px solid rgba(10,22,51,0.10)",
                }}
              >
                <ShieldCheck size={18} color="rgba(27,91,255,1)" />
              </div>
              <div>
                <div style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: 16, letterSpacing: "-0.02em" }}>
                  Governance Intelligence
                </div>
                <div style={{ fontSize: 11.5, fontWeight: 900, color: "rgba(11,19,36,0.55)", marginTop: 1 }}>
                  Operating system for organizational governance
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
              <button
                className="gov-btn"
                onClick={() => {
                  setBoardMode((v) => !v);
                  setBoardNarrative((n) => (n === "executive" ? "audit" : "executive"));
                }}
                style={{ display: "flex", gap: 10, alignItems: "center" }}
              >
                <Eye size={16} /> Boardroom Mode
                <span className="gov-kbd" style={{ marginLeft: 6 }}>
                  ⇧ ⌁
                </span>
              </button>

              <button className="gov-btn primary" onClick={scrollToCopilot}>
                Engage Copilot <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Landing */}
        <section
          style={{
            position: "relative",
            padding: "68px 22px 26px",
            maxWidth: 1400,
            margin: "0 auto",
          }}
        >
          <div style={{ position: "relative", borderRadius: 30, overflow: "hidden" }}>
            <AuroraNetwork reduced={reduced} />

            <div
              style={{
                position: "relative",
                padding: "58px 22px 34px",
                border: "1px solid rgba(10,22,51,0.10)",
                background: "rgba(255,255,255,0.20)",
                backdropFilter: "blur(18px)",
                boxShadow: CAP.shadow,
              }}
            >
              <div className="gov-chip gov-aurora" style={{ borderColor: "rgba(212,175,55,0.38)" }}>
                <Sparkles size={14} /> Governance signals · live intelligence · board-ready decisions
              </div>

              <h1 className="gov-h1" style={{ marginTop: 16 }}>
                Governance. Reimagined.
              </h1>

              <p style={{ maxWidth: 880, marginTop: 14, fontSize: 16.5, fontWeight: 800, color: "rgba(11,19,36,0.68)", lineHeight: 1.6 }}>
                The first AI-powered platform that transforms compliance, nominations, approvals, audits and policy governance into a living intelligence system.
              </p>

              <div style={{ display: "flex", gap: 12, marginTop: 20, flexWrap: "wrap" }}>
                <button
                  className="gov-btn primary"
                  onClick={() => {
                    scrollToCopilot();
                    setTimeout(() => copilotRef.current?.focus?.(), 350);
                  }}
                >
                  Interact with governance copilot <ArrowRight size={16} />
                </button>
                <button className="gov-btn" onClick={() => document.getElementById("command")?.scrollIntoView({ behavior: "smooth" })}>
                  Explore command center
                </button>
              </div>

              <div style={{ marginTop: 26, display: "flex", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
                <div className="gov-scrollhint">
                  <ChevronRight size={18} color="rgba(27,91,255,1)" />
                  Scroll storytelling engaged. The system explains itself as you move.
                </div>
                <div className="gov-scrollhint">
                  <Info size={18} />
                  Premium signal cards. No tables-first experience.
                </div>
              </div>
            </div>
          </div>

          <div className="gov-fade-in" data-inview="false" style={{ marginTop: 26 }}>
            <div id="command" />
            <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {tiles.slice(0, 3).map((t) => (
                <GovernanceTile key={t.key} {...t} />
              ))}
            </div>
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
              {tiles.slice(3).map((t) => (
                <GovernanceTile key={t.key} {...t} />
              ))}
            </div>
          </div>

          <AnimatePresence>
            {boardMode ? (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}>
                <BoardroomNarrative activeNarrative={boardNarrative} narratives={narratives} />
              </motion.div>
            ) : null}
          </AnimatePresence>
        </section>

        {/* Copilot */}
        <section id="copilot" style={{ padding: "20px 22px 40px", maxWidth: 1400, margin: "0 auto" }}>
          <div className="gov-surface" style={{ padding: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14, flexWrap: "wrap" }}>
              <div>
                <div className="gov-chip" style={{ borderColor: "rgba(27,91,255,0.35)" }}>
                  <BrainCircuit size={14} /> Governance Copilot
                </div>
                <h2 className="gov-h2" style={{ marginTop: 12 }}>
                  What would you like to govern today?
                </h2>
                <p className="gov-fineprint" style={{ marginTop: 10, maxWidth: 820 }}>
                  Interact with a governance copilot. Ask compliance questions, request audits, review nominations, interpret policy intent, analyze risk exposure, or generate executive reporting.
                </p>
              </div>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
                <div className="gov-chip" style={{ borderColor: "rgba(212,175,55,0.40)", color: "rgba(154,122,19,1)" }}>
                  <Zap size={14} /> Cards respond in moments
                </div>
                <div className="gov-chip" style={{ borderColor: "rgba(10,22,51,0.14)" }}>
                  <ShieldAlert size={14} /> Transparent reasoning notes
                </div>
              </div>
            </div>

            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr", gap: 12 }}>
              <div style={{ display: "flex", gap: 12, alignItems: "stretch", flexWrap: "wrap" }}>
                <input
                  ref={copilotRef}
                  className="gov-copilot-input"
                  value={copilotPrompt}
                  onChange={(e) => setCopilotPrompt(e.target.value)}
                  placeholder={placeholderExample}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onGovern();
                  }}
                  aria-label="Governance prompt"
                />
                <button
                  className="gov-btn primary"
                  onClick={onGovern}
                  disabled={sending || !copilotPrompt.trim()}
                  style={{ minWidth: 220, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}
                >
                  {sending ? (
                    <>
                      <span
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: 999,
                          background: "rgba(8,16,36,1)",
                          boxShadow: "0 0 0 6px rgba(27,91,255,0.14)",
                        }}
                      />
                      Governing…
                    </>
                  ) : (
                    <>
                      Interact <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {suggestions.map((b) => (
                  <button
                    key={b.label}
                    className="gov-btn"
                    onClick={() => setCopilotPrompt(b.prompt)}
                    style={{ padding: "9px 12px", borderRadius: 999, fontWeight: 950 }}
                  >
                    {b.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            {lastPrompt ? (
              <div className="gov-chip" style={{ marginBottom: 12, borderColor: "rgba(27,91,255,0.28)" }}>
                <Info size={14} /> Last request: <span style={{ color: CAP.textDim, fontWeight: 950 }}>{lastPrompt}</span>
              </div>
            ) : (
              <div className="gov-fineprint" style={{ padding: "10px 2px 16px" }}>
                Nothing here yet. Start your first governance interaction.
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: boardMode ? "1fr" : "repeat(2, 1fr)", gap: 14 }}>
              <AnimatePresence>
                {cards.length ? (
                  cards.map((c) => <GovernanceCard key={c.id} card={c} />)
                ) : (
                  <motion.div
                    className="gov-card"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    style={{ gridColumn: "1 / -1" }}
                  >
                    <div className="gov-cardTitle">
                      <span
                        style={{
                          width: 34,
                          height: 34,
                          borderRadius: 14,
                          display: "grid",
                          placeItems: "center",
                          background: "rgba(27,91,255,0.12)",
                          border: "1px solid rgba(10,22,51,0.12)",
                          color: "rgba(27,91,255,1)",
                        }}
                      >
                        <Sparkles size={16} />
                      </span>
                      <b>Governance cards arrive here</b>
                    </div>
                    <div className="gov-cardBody">
                      The copilot doesn’t ask you to submit forms. It helps you govern—then explains the decision.
                    </div>
                    <div className="gov-cardMeta">
                      <span className="gov-tag gold">Outcome-first</span>
                      <span className="gov-tag blue">Transparency included</span>
                      <span className="gov-tag blue">Authority signals</span>
                    </div>
                    <div className="gov-fineprint" style={{ marginTop: 12 }}>
                      Tip: Use a quick prompt chip above to generate a realistic board-ready response.
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </section>

        {/* Visual section anchors (future workspaces) */}
        <section style={{ padding: "14px 22px 72px", maxWidth: 1400, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 16, alignItems: "stretch" }}>
            <div className="gov-surface" style={{ padding: 18 }}>
              <div className="gov-chip" style={{ borderColor: "rgba(212,175,55,0.36)", color: "rgba(154,122,19,1)" }}>
                <Users size={14} /> Nomination experience (preview)
              </div>
              <h2 className="gov-h2" style={{ marginTop: 12 }}>
                Select future leaders. Not forms.
              </h2>
              <p className="gov-fineprint" style={{ marginTop: 10 }}>
                Multi-step nomination flow with candidate cards, eligibility verification, approval forecasting, and a timeline view of stakeholder involvement.
              </p>

              <div className="gov-fineprint" style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap" }}>
                <span className="gov-tag gold">Skill matching</span>
                <span className="gov-tag blue">Forecasted approvals</span>
                <span className="gov-tag blue">Stakeholder map</span>
                <span className="gov-tag gold">Executive recommendation</span>
              </div>

              <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button
                  className="gov-btn"
                  onClick={() => {
                    setCopilotPrompt("Nomination review. Recommend a board slate. Forecast approvals and eligibility.");
                    setTimeout(() => onGovern(), 50);
                  }}
                >
                  Generate nomination recommendation <ArrowRight size={16} />
                </button>
                <a className="gov-mutedLink" href="#copilot" onClick={(e) => { e.preventDefault(); scrollToCopilot(); }}>
                  Continue in Copilot →
                </a>
              </div>
            </div>

            <div className="gov-surface" style={{ padding: 18 }}>
              <div className="gov-chip" style={{ borderColor: "rgba(27,91,255,0.34)" }}>
                <ShieldCheck size={14} /> Compliance workspace (preview)
              </div>
              <h2 className="gov-h2" style={{ marginTop: 12 }}>
                Policies become living documents.
              </h2>
              <p className="gov-fineprint" style={{ marginTop: 10 }}>
                Heatmaps for adoption, department compliance maps, acknowledgment analytics, and readiness forecasting—visual-first and built for decision-makers.
              </p>
              <div style={{ marginTop: 14 }}>
                <div className="gov-timelineLine" />
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  {capabilities.length ? (
                    capabilities.map((s, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: 999,
                            background: i % 2 === 0 ? "rgba(27,91,255,1)" : "rgba(212,175,55,1)",
                            boxShadow: `0 0 0 6px ${i % 2 === 0 ? "rgba(27,91,255,0.15)" : "rgba(212,175,55,0.16)"}`,
                          }}
                        />
                        <div style={{ fontWeight: 950, color: "rgba(11,19,36,0.72)" }}>{s}</div>
                      </div>
                    ))
                  ) : (
                    <div className="gov-fineprint">Loading capabilities...</div>
                  )}
                </div>
              </div>

              <div style={{ marginTop: 16 }}>
                <button
                  className="gov-btn primary"
                  onClick={() => {
                    setCopilotPrompt("Compliance health check. Visualize policy adoption heatmaps and readiness gaps.");
                    setTimeout(() => onGovern(), 50);
                  }}
                >
                  Explore compliance intelligence <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 16 }} className="gov-fineprint">
            Next implementation phase will replace these previews with full visual workspaces (nomination, compliance, risk universe, audit timeline, approval pathways, board-ready narrative).
          </div>
        </section>
      </div>
    </>
  );
}

