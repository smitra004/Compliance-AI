
import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D from "3d-force-graph";
import SpriteText from "three-spritetext";

/**
 * DigitalTwin — the 3D policy digital twin.
 *
 * Ported from ComplianceAI-final-merged's Twin3D component (3d-force-graph +
 * three-spritetext), unchanged in behaviour: regulations connect to the
 * clauses they define, clauses to the findings they triggered, findings to
 * the documents that contain them. Drag to orbit, scroll to zoom, click any
 * node to focus the camera on it.
 *
 * Self-contained: only needs the raw `scans` list (as returned by the
 * backend's /scans endpoint) — it builds its own graph, labels and colors,
 * so no other file/theme/global needs to change to use it.
 *
 * Props:
 *   - title, subtitle : header text
 *   - height          : canvas height in px (default 560)
 *   - scans           : array of scan records (scan_id, document_name,
 *                        created_at, compliance_score, total_violations,
 *                        violations: [{ severity, source_regulation,
 *                        citation:{clause,text}, title, id,
 *                        estimated_fine_min/max }])
 */

const TWIN_COLORS = {
  regulation: "#c95a32",
  clause: "#b9862f",
  document: "#1b1b1b",
  violation: "#c24a3f",
};

const REG_LABEL = {
  gdpr: "GDPR",
  sox: "SOX",
  iso27001: "ISO 27001",
  internal_security: "Internal Security",
  internal_hr: "Internal HR",
  internal: "Internal Policy",
};
const SEV_LABEL = { P1: "Critical", P2: "High", P3: "Medium", P4: "Low" };

function fmtINR(n) {
  if (n == null) return "—";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(1)} Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`;
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
}
function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function buildTwin(scans) {
  const nodes = new Map();
  const links = [];
  const add = (id, node) => {
    if (!nodes.has(id)) nodes.set(id, { id, ...node });
    return id;
  };

  // A document that's been (re-)scanned more than once shows up multiple
  // times in `scans` (one ScanRecord per upload), each with its own
  // scan_id — which would otherwise produce a duplicate document node
  // (same label, different id) plus duplicate clause/violation nodes
  // pulled in from the stale, superseded scan. Keep only the most recent
  // scan per document_name so the twin reflects each document's current
  // state exactly once.
  const latestByDoc = new Map();
  for (const s of scans) {
    const key = s.document_name;
    const prev = latestByDoc.get(key);
    if (!prev || new Date(s.created_at) > new Date(prev.created_at)) {
      latestByDoc.set(key, s);
    }
  }
  const dedupedScans = [...latestByDoc.values()];

  for (const s of dedupedScans) {
    const docId = add(`doc:${s.scan_id}`, {
      label: s.document_name,
      group: "document",
      val: 7,
      meta: { kind: "Document", score: s.compliance_score, findings: s.total_violations, when: fmtDate(s.created_at) },
    });
    for (const v of s.violations || []) {
      const regKey = v.source_regulation || "internal";
      const regId = add(`reg:${regKey}`, {
        label: REG_LABEL[regKey] || regKey,
        group: "regulation",
        val: 13,
        meta: { kind: "Regulation" },
      });
      const clauseName = v.citation?.clause || v.title;
      const clauseId = add(`clause:${regKey}:${clauseName}`, {
        label: clauseName,
        group: "clause",
        val: 5,
        meta: { kind: "Policy clause", text: v.citation?.text },
      });
      const vioId = add(`vio:${v.id}`, {
        label: v.title,
        group: "violation",
        val: 4,
        meta: {
          kind: "Finding",
          severity: SEV_LABEL[v.severity] || v.severity,
          fine: `${fmtINR(v.estimated_fine_min)}–${fmtINR(v.estimated_fine_max)}`,
        },
      });
      links.push({ source: regId, target: clauseId });
      links.push({ source: clauseId, target: vioId });
      links.push({ source: vioId, target: docId });
    }
    if (!s.violations?.length) {
      const regId = add("reg:internal_security", { label: "Internal Security", group: "regulation", val: 13, meta: { kind: "Regulation" } });
      links.push({ source: regId, target: docId });
    }
  }
  return { nodes: [...nodes.values()], links };
}


    export default function DigitalTwin({
    title = "Compliance Digital Twin",
    subtitle = "Your compliance estate, alive in three dimensions.",
    height = 620,
    scan = null,
  }) {
  const mountRef = useRef(null);
  const graphRef = useRef(null);
  const [selected, setSelected] = useState(null);
  const data = useMemo(() => {
    if (!scan) return { nodes: [], links: [] };
    return buildTwin([scan]);
  }, [scan?.scan_id]);

  const zoom = (factor) => {
    const g = graphRef.current;
    if (!g) return;
    const cam = g.camera();
    const { x, y, z } = cam.position;
    g.cameraPosition({ x: x * factor, y: y * factor, z: z * factor }, undefined, 350);
  };

  useEffect(() => {
    if (!mountRef.current) return;
    const el = mountRef.current;
    const g = ForceGraph3D({ controlType: "orbit" })(el)
      .backgroundColor("#fbf9f7")
      .width(el.clientWidth || el.offsetWidth || 800)
      .height(height)
      .nodeVal("val")
      .nodeColor((n) => TWIN_COLORS[n.group] || "#666")
      .nodeOpacity(0.92)
      .nodeThreeObjectExtend(true)
      .nodeThreeObject((n) => {
        const t = new SpriteText(n.label.length > 26 ? n.label.slice(0, 25) + "…" : n.label);
        t.color = "#1b1b1b";
        t.backgroundColor = "rgba(255,255,255,0.85)";
        t.padding = 1.5;
        t.borderRadius = 2;
        t.textHeight = n.group === "regulation" ? 4.4 : 3.1;
        t.fontFace = "Inter, sans-serif";
        t.position.y = -(Math.cbrt(n.val) * 4 + 5);
        return t;
      })
      .linkColor(() => "#c9c2ba")
      .linkOpacity(0.55)
      .linkWidth(0.8)
      .linkDirectionalParticles(1)
      .linkDirectionalParticleSpeed(0.004)
      .linkDirectionalParticleWidth(1.6)
      .linkDirectionalParticleColor(() => "#c95a32")
      .onNodeClick((n) => {
        setSelected(n);
        const dist = 120;
        const ratio = 1 + dist / Math.hypot(n.x || 1, n.y || 1, n.z || 1);
        g.cameraPosition({ x: (n.x || 0) * ratio, y: (n.y || 0) * ratio, z: (n.z || 0) * ratio }, n, 900);
      })
      .onBackgroundClick(() => setSelected(null));
    g.graphData(data);
    g.cooldownTicks(100);
    g.cooldownTime(3500);

    g.onEngineStop(() => {
        g.pauseAnimation();
    });
    graphRef.current = g;

    // Keep the graph's internal canvas in sync with its actual container size —
    // a one-time clientWidth read (or only listening for window resize) leaves
    // the graph stuck at whatever width the container happened to have at the
    // moment it mounted (e.g. a hidden tab, a not-yet-settled flex layout),
    // which is what causes it to render squeezed into only part of the card.
    let raf = null;
    const applySize = () => {
      const w = el.clientWidth || el.offsetWidth;
      if (w > 0) g.width(w);
      g.height(el.clientHeight || height);
    };
    const ro = new ResizeObserver(() => {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(applySize);
    });
    ro.observe(el);
    applySize();
    window.addEventListener("resize", applySize);

    return () => {
      if (raf) cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("resize", applySize);
      g._destructor?.();
      graphRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    graphRef.current?.height(height);
  }, [height]);

  useEffect(() => {
    if (!graphRef.current) return;

      graphRef.current.graphData(data);
      graphRef.current.cooldownTicks(80);

    }, [scan?.scan_id]);

  return (
    <div style={{ position: "relative", overflow: "hidden", borderRadius: 18, border: "1px solid rgba(22,18,14,0.10)", background: "#fbf9f7", width: "100%", minWidth: 0, boxSizing: "border-box" }}>
      <div style={{ padding: "24px 28px 4px" }}>
        <div style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontStyle: "italic", fontSize: 26, color: "#16120E", lineHeight: 1.1 }}>
          {title}
        </div>
        <div style={{ fontSize: 12.5, color: "#8C8278", marginTop: 4 }}>{subtitle}</div>
        <div style={{ fontSize: 11, color: "#8C8278", marginTop: 6 }}>
          Drag to orbit · scroll to zoom · click a node to focus
        </div>
      </div>

      <div style={{ position: "relative", height, width: "100%", minWidth: 0 }}>
        <div
          style={{
            position: "absolute", left: 16, top: 16, zIndex: 10,
            display: "flex", flexDirection: "column", gap: 6,
            borderRadius: 12, border: "1px solid rgba(22,18,14,0.10)",
            background: "rgba(255,255,255,0.95)", padding: "12px 16px",
            fontSize: 11, backdropFilter: "blur(12px)",
          }}
        >
          {Object.entries({ regulation: "Regulation", clause: "Policy clause", violation: "Finding", document: "Document" }).map(([k, lbl]) => (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, color: "#5C5248", fontWeight: 500 }}>
              <span style={{ width: 10, height: 10, borderRadius: "50%", background: TWIN_COLORS[k], flexShrink: 0 }} />
              {lbl}
            </div>
          ))}
        </div>

        {selected && (
          <div
            style={{
              position: "absolute", right: 16, top: 16, zIndex: 10, width: 280,
              borderRadius: 12, border: "1px solid rgba(22,18,14,0.10)",
              background: "rgba(255,255,255,0.96)", padding: 16, fontSize: 13,
              backdropFilter: "blur(12px)", boxShadow: "0 4px 16px rgba(22,18,14,0.10)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 8 }}>
              <div>
                <div style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8C8278" }}>
                  {selected.meta?.kind}
                </div>
                <div style={{ marginTop: 4, fontFamily: "'Instrument Serif', Georgia, serif", fontStyle: "italic", fontSize: 17, color: "#16120E" }}>
                  {selected.label}
                </div>
              </div>
              <button
                onClick={() => setSelected(null)}
                aria-label="Close"
                style={{ border: "none", background: "none", cursor: "pointer", color: "#8C8278", fontSize: 14, lineHeight: 1 }}
              >
                ✕
              </button>
            </div>
            {selected.meta?.severity && (
              <div style={{
                marginTop: 8, display: "inline-block", padding: "3px 10px", borderRadius: 99,
                fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
                background: "rgba(184,92,56,0.14)", color: "#B85C38",
              }}>
                {selected.meta.severity}
              </div>
            )}
            {selected.meta?.score != null && (
              <div style={{ marginTop: 8, fontSize: 12, color: "#5C5248" }}>
                Score {selected.meta.score} · {selected.meta.findings} finding(s) · {selected.meta.when}
              </div>
            )}
            {selected.meta?.fine && <div style={{ marginTop: 6, fontSize: 12, color: "#5C5248" }}>Exposure {selected.meta.fine}</div>}
            {selected.meta?.text && <div style={{ marginTop: 8, fontSize: 12, color: "#5C5248" }}>{selected.meta.text}</div>}
          </div>
        )}

        <div
          style={{
            position: "absolute", right: 16, bottom: 16, zIndex: 10,
            display: "flex", flexDirection: "column", gap: 4,
            borderRadius: 12, border: "1px solid rgba(22,18,14,0.10)",
            background: "rgba(255,255,255,0.95)", padding: 4,
            backdropFilter: "blur(12px)", boxShadow: "0 4px 16px rgba(22,18,14,0.10)",
          }}
        >
          <button
            onClick={() => zoom(0.8)}
            aria-label="Zoom in"
            title="Zoom in"
            style={{
              width: 30, height: 30, display: "grid", placeItems: "center",
              border: "none", background: "none", cursor: "pointer",
              color: "#16120E", fontSize: 16, fontWeight: 700, borderRadius: 8,
            }}
          >
            +
          </button>
          <div style={{ height: 1, background: "rgba(22,18,14,0.10)" }} />
          <button
            onClick={() => zoom(1.25)}
            aria-label="Zoom out"
            title="Zoom out"
            style={{
              width: 30, height: 30, display: "grid", placeItems: "center",
              border: "none", background: "none", cursor: "pointer",
              color: "#16120E", fontSize: 16, fontWeight: 700, borderRadius: 8,
            }}
          >
            −
          </button>
        </div>

        <div ref={mountRef} style={{ width: "100%", height: "100%", minWidth: 0 }} />
      </div>

      {data.nodes.length <= 1 && (
        <p style={{ margin: "0", padding: "0 28px 20px", fontSize: 13, color: "#8C8278" }}>
          The twin grows as you scan — run more documents to add nodes to the graph.
        </p>
      )}
    </div>
  );
}
