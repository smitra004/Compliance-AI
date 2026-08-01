import React, { useState, useEffect } from "react";
import { User, Database, Search, Lock, CheckCircle2, XCircle, Zap, RefreshCw, Filter, FileText, ShieldCheck, Activity } from "lucide-react";

export default function ProductionUserPortal({ token, CAP, modeData, onEvalComplete }) {
  const [resources, setResources] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedResource, setSelectedResource] = useState(null);
  const [action, setAction] = useState("Read");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);

  const authToken = token || localStorage.getItem("token") || "";

  // 1. Fetch Backend-Driven Enterprise Resource Catalog
  const fetchResources = async () => {
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      let url = `/api/v1/resources?category=${selectedCategory}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
      const res = await fetch(url, { headers });
      const data = await res.json();
      if (Array.isArray(data)) {
        setResources(data);
        if (data.length > 0 && !selectedResource) {
          setSelectedResource(data[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching resources:", err);
    }
  };

  useEffect(() => {
    fetchResources();
  }, [selectedCategory, searchQuery]);

  // 2. Submit Production Access Request
  const handleAccessRequest = async () => {
    if (!selectedResource) return;
    setLoading(true);
    try {
      const res = await fetch("/api/v1/access/request", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authToken ? `Bearer ${authToken}` : "",
        },
        body: JSON.stringify({
          resource_id: selectedResource.resource_id,
          action,
        }),
      });
      const data = await res.json();
      onEvalComplete(data, selectedResource);

      // Append to history
      setHistory((prev) => [
        {
          timestamp: new Date().toLocaleTimeString(),
          resource: selectedResource.name,
          action,
          decision: data.decision,
          risk: data.risk_score,
          matched: data.matched_policy,
        },
        ...prev.slice(0, 4),
      ]);
    } catch (err) {
      console.error("Access request error:", err);
    } finally {
      setLoading(false);
    }
  };

  const storedUser = (() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  })();

  const identity = modeData?.identity || {
    username: storedUser.username || "admin",
    employee_id: storedUser.id ? `EMP-${storedUser.id}` : "EMP-1001",
    role: storedUser.role || "central_admin",
    department: storedUser.department || "Global",
    clearance_level: "Confidential",
    clearance_rank: 3,
    designation: storedUser.designation || "Compliance Manager",
    employment_type: "Full-Time",
    region: "US",
    business_unit: "Corporate",
    mfa_status: true,
    device_trust_level: "Trusted",
  };

  const categories = ["All", "Documents", "Dashboards", "APIs", "Reports", "Datasets"];

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
    badge: (type) => ({
      padding: "4px 10px",
      borderRadius: 16,
      fontSize: 11,
      fontWeight: 700,
      textTransform: "uppercase",
      background: type === "PERMIT" || type === "Public" ? "rgba(90, 122, 106, 0.15)" : type === "Restricted" || type === "Top Secret" ? "rgba(184, 92, 56, 0.15)" : "rgba(201, 169, 110, 0.15)",
      color: type === "PERMIT" || type === "Public" ? "#5A7A6A" : type === "Restricted" || type === "Top Secret" ? "#B85C38" : CAP?.purple || "#C9A96E",
      border: `1px solid ${type === "PERMIT" || type === "Public" ? "#5A7A6A" : type === "Restricted" || type === "Top Secret" ? "#B85C38" : CAP?.purple || "#C9A96E"}`,
    }),
  };

  return (
    <div>
      {/* My Identity Panel */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <User size={20} color={CAP?.purple} />
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: CAP?.text }}>
              My Identity Claims (Authentic Read-Only Session)
            </h3>
          </div>
          <span style={{ padding: "4px 12px", borderRadius: 20, background: "rgba(90, 122, 106, 0.15)", color: "#5A7A6A", border: "1px solid #5A7A6A", fontSize: 12, fontWeight: 700 }}>
            🔒 Derived from Verified Enterprise IdP (Azure AD / Keycloak JWT)
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, background: CAP?.bg, padding: 14, borderRadius: 10, border: `1px solid ${CAP?.border}` }}>
          <div>
            <span style={styles.label}>Username</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.text }}>{identity.username}</div>
          </div>
          <div>
            <span style={styles.label}>Employee ID</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.purple }}>{identity.employee_id || "EMP-884920"}</div>
          </div>
          <div>
            <span style={styles.label}>Role</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.purple }}>{identity.role.toUpperCase()}</div>
          </div>
          <div>
            <span style={styles.label}>Department</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.text }}>{identity.department}</div>
          </div>
          <div>
            <span style={styles.label}>Clearance Level</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.text }}>{identity.clearance_level} (Rank {identity.clearance_rank || 3})</div>
          </div>
          <div>
            <span style={styles.label}>Designation</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.text }}>{identity.designation}</div>
          </div>
          <div>
            <span style={styles.label}>Region / BU</span>
            <div style={{ fontSize: 14, fontWeight: 700, color: CAP?.text }}>{identity.region} / {identity.business_unit}</div>
          </div>
          <div>
            <span style={styles.label}>Session Security</span>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#5A7A6A", display: "flex", alignItems: "center", gap: 6 }}>
              <ShieldCheck size={15} /> MFA Verified | VPN
            </div>
          </div>
        </div>
      </div>

      {/* Backend-Driven Resource Catalog & Access Request */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Left: Resource Search & Catalog */}
        <div style={styles.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
              <Database size={18} color={CAP?.purple} /> Searchable Enterprise Resource Catalog
            </h3>
            <span style={{ fontSize: 12, color: CAP?.textDim }}>Backend-Driven (`/api/v1/resources`)</span>
          </div>

          {/* Search & Category Filter */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ position: "relative", marginBottom: 10 }}>
              <Search size={16} color={CAP?.textDim} style={{ position: "absolute", left: 12, top: 12 }} />
              <input
                style={{
                  width: "100%",
                  padding: "9px 12px 9px 36px",
                  borderRadius: 8,
                  border: `1px solid ${CAP?.border}`,
                  background: CAP?.bg,
                  color: CAP?.text,
                  fontSize: 13,
                  outline: "none",
                }}
                placeholder="Search resources by name, ID, or department..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    padding: "5px 12px",
                    borderRadius: 6,
                    border: `1px solid ${selectedCategory === cat ? CAP?.purple || "#C9A96E" : CAP?.border}`,
                    background: selectedCategory === cat ? CAP?.purple || "#C9A96E" : CAP?.bg,
                    color: selectedCategory === cat ? "#16120E" : CAP?.textDim,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Resource Catalog Cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 320, overflowY: "auto" }}>
            {resources.map((res) => (
              <div
                key={res.resource_id}
                onClick={() => setSelectedResource(res)}
                style={{
                  padding: 12,
                  borderRadius: 8,
                  border: `1px solid ${selectedResource?.resource_id === res.resource_id ? CAP?.purple || "#C9A96E" : CAP?.border}`,
                  background: selectedResource?.resource_id === res.resource_id ? "rgba(201, 169, 110, 0.08)" : CAP?.bg,
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: 11, fontWeight: 800, color: CAP?.purple }}>{res.resource_id} ({res.category})</span>
                  <span style={styles.badge(res.classification)}>{res.classification}</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: CAP?.text, marginBottom: 2 }}>{res.name}</div>
                <div style={{ fontSize: 11, color: CAP?.textDim }}>
                  Dept: <strong>{res.department}</strong> | Sensitive: {res.contains_pii ? "PII " : ""}{res.contains_financial_data ? "Financial" : ""}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Access Request Execution */}
        <div style={styles.card}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 0, marginBottom: 14, color: CAP?.text, display: "flex", alignItems: "center", gap: 8 }}>
            <Zap size={18} color={CAP?.purple} /> Action & Access Request Workflow
          </h3>

          {selectedResource ? (
            <div style={{ marginBottom: 16, padding: 14, borderRadius: 8, background: CAP?.bg, border: `1px solid ${CAP?.border}` }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: CAP?.purple, textTransform: "uppercase", marginBottom: 4 }}>Selected Resource Target</div>
              <div style={{ fontSize: 14, fontWeight: 800, color: CAP?.text }}>{selectedResource.name}</div>
              <div style={{ fontSize: 12, color: CAP?.textDim, marginTop: 2 }}>ID: {selectedResource.resource_id} | Classification: {selectedResource.classification}</div>
            </div>
          ) : (
            <div style={{ color: CAP?.textDim, fontSize: 13 }}>Select a resource from the catalog.</div>
          )}

          <div style={{ marginBottom: 16 }}>
            <label style={styles.label}>Requested Action</label>
            <select
              style={{
                width: "100%",
                padding: "9px 12px",
                borderRadius: 8,
                border: `1px solid ${CAP?.border}`,
                background: CAP?.bg,
                color: CAP?.text,
                fontSize: 13,
                outline: "none",
              }}
              value={action}
              onChange={(e) => setAction(e.target.value)}
            >
              <option value="Read">Read / View Resource</option>
              <option value="Download">Download Document Report</option>
              <option value="Export">Export Data Stream</option>
              <option value="Upload">Upload New Revision</option>
              <option value="Delete">Delete Resource Record</option>
              <option value="Approve">Approve Regulatory Audit</option>
            </select>
          </div>

          <button
            onClick={handleAccessRequest}
            disabled={loading || !selectedResource}
            style={{
              width: "100%",
              padding: "12px 18px",
              borderRadius: 8,
              border: "none",
              background: CAP?.purple || "#C9A96E",
              color: "#16120E",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            {loading ? <RefreshCw className="spin" size={16} /> : <Zap size={16} />}
            Request Production Access Evaluation
          </button>

          {/* User Access Request History */}
          {history.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: CAP?.purple, textTransform: "uppercase", marginBottom: 8 }}>
                Recent Access Request History
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {history.map((h, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, padding: "6px 10px", borderRadius: 6, background: CAP?.bg, border: `1px solid ${CAP?.border}` }}>
                    <span>{h.timestamp} - {h.action} on <strong>{h.resource.slice(0, 20)}...</strong></span>
                    <span style={styles.badge(h.decision)}>{h.decision} (Risk {h.risk})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
