import { useEffect, useRef, useState } from "react";
import { Bell, X, CheckCircle2, ShieldAlert, Wrench } from "lucide-react";

const WS_BASE = import.meta.env.VITE_WS_BASE ||
  `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

const ICONS = {
  scan_completed: CheckCircle2,
  remediation_applied: Wrench,
  connected: Bell,
};

export default function NotificationCenter() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      try {
        const ws = new WebSocket(`${WS_BASE}/notifications`);
        wsRef.current = ws;
        ws.onopen = () => !cancelled && setConnected(true);
        ws.onclose = () => {
          if (cancelled) return;
          setConnected(false);
          retryRef.current = setTimeout(connect, 4000); // auto-reconnect
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (evt) => {
          try {
            const payload = JSON.parse(evt.data);
            if (payload.type === "connected") return;
            setItems(prev => [{ timestamp: new Date().toISOString(), ...payload, id: `${Date.now()}-${Math.random()}`, read: false }, ...prev].slice(0, 30));
          } catch { /* ignore malformed frames */ }
        };
      } catch { /* WebSocket unsupported / blocked — bell just stays static */ }
    }

    connect();
    return () => { cancelled = true; clearTimeout(retryRef.current); wsRef.current?.close(); };
  }, []);

  const unread = items.filter(i => !i.read).length;

  function markAllRead() {
    setItems(prev => prev.map(i => ({ ...i, read: true })));
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => { setOpen(o => !o); if (!open) markAllRead(); }}
        title={connected ? "Live notifications connected" : "Reconnecting…"}
        style={{
          position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 38, height: 38, borderRadius: 10, cursor: "pointer",
          background: "transparent", border: "1px solid rgba(22,18,14,0.12)", color: "inherit",
        }}
      >
        <Bell size={16}/>
        <span style={{
          position: "absolute", top: 6, right: 6, width: 6, height: 6, borderRadius: "50%",
          background: connected ? "#5A7A6A" : "#B85C38",
        }}/>
        {unread > 0 && (
          <span style={{
            position: "absolute", top: -4, right: -4, minWidth: 16, height: 16, borderRadius: 999,
            background: "#B85C38", color: "#fff", fontSize: 10, fontWeight: 700,
            display: "flex", alignItems: "center", justifyContent: "center", padding: "0 3px",
          }}>{unread}</span>
        )}
      </button>

      {open && (
        <div style={{
          position: "absolute", right: 0, top: 46, width: 320, maxHeight: 380, overflowY: "auto",
          background: "var(--panel, #fff)", border: "1px solid rgba(22,18,14,0.10)", borderRadius: 14,
          boxShadow: "0 24px 60px -22px rgba(22,18,14,0.25)", zIndex: 50, padding: 8,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 8px 10px" }}>
            <strong style={{ fontSize: 13 }}>Live activity</strong>
            <X size={14} style={{ cursor: "pointer" }} onClick={() => setOpen(false)}/>
          </div>
          {items.length === 0 && (
            <div style={{ padding: "18px 8px", fontSize: 12.5, opacity: 0.6, textAlign: "center" }}>
              Nothing yet — this fills in as scans complete, live.
            </div>
          )}
          {items.map(i => {
            const Icon = ICONS[i.type] || ShieldAlert;
            return (
              <div key={i.id} style={{
                display: "flex", gap: 10, padding: "10px 8px", borderRadius: 10,
                borderBottom: "1px solid rgba(22,18,14,0.06)",
              }}>
                <Icon size={15} style={{ flexShrink: 0, marginTop: 2, opacity: 0.7 }}/>
                <div style={{ fontSize: 12.5 }}>
                  {i.type === "scan_completed" && (
                    <div><strong>{i.document_name}</strong> scanned — {i.compliance_score}% compliant, {i.total_violations} finding(s).</div>
                  )}
                  {i.type === "remediation_applied" && (
                    <div>{i.resolved_count} violation(s) remediated on <strong>{i.document_name}</strong> — now {i.compliance_score}%.</div>
                  )}
                  <div style={{ opacity: 0.5, fontSize: 10.5, marginTop: 2 }}>{new Date(i.timestamp).toLocaleTimeString()}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
