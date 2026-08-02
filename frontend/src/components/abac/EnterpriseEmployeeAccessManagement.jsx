import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  UserCheck,
  KeyRound,
  Lock,
  CheckCircle2,
  XCircle,
  Search,
  Building2,
  Sliders,
  Sparkles,
  Eye,
  Download,
  FileSpreadsheet,
  Trash2,
  Fingerprint,
  DollarSign,
  AlertTriangle,
  Check,
  X,
  Save,
} from "lucide-react";
import { apiFetch } from "../../api";

const DEFAULT_CAP = {
  purple: "#C9A96E",
  purpleDark: "#B8923A",
  purpleGlow: "rgba(201, 169, 110, 0.16)",
  cyan: "#4A6080",
  cyanDark: "#3A4D66",
  cyanGlow: "rgba(74, 96, 128, 0.14)",
  blue: "#4A6080",
  teal: "#5A7A6A",
  orange: "#C2683E",
  red: "#B85C38",
  amber: "#C9A96E",
  green: "#5A7A6A",
  bg: "#FAF7F2",
  panel: "#FFFFFF",
  border: "rgba(22, 18, 14, 0.09)",
  borderBt: "rgba(201, 169, 110, 0.30)",
  text: "#16120E",
  textDim: "#5C5248",
  textFaint: "#8C8278",
};

// ─── GOVERNANCE POLICY MATRICES ─────────────────────────────────────────────
// Source of truth: "Table 1: Statutory Regulation Authorizations" and
// "Table 2: Feature Access" governance tables. Role keys mirror the backend
// ROLE_PERMISSIONS dict in app/rbac.py — "admin" here means "Departmental
// Admin" (scoped to own department) and "central_admin" means the table's
// "Admin" row (global/unscoped).
//
// Regulation access levels: "full" | "own_dept" | "read_only" | "none"
const ROLE_REGULATION_MATRIX = {
  central_admin: { GDPR: "full", SOX: "full", ISO27001: "full", HIPAA: "full", INTERNALSECURITY: "full", INTERNALHR: "full" },
  admin: { GDPR: "full", SOX: "full", ISO27001: "full", HIPAA: "full", INTERNALSECURITY: "full", INTERNALHR: "full" },
  manager: { GDPR: "none", SOX: "full", ISO27001: "full", HIPAA: "none", INTERNALSECURITY: "full", INTERNALHR: "full" },
  auditor: { GDPR: "read_only", SOX: "read_only", ISO27001: "read_only", HIPAA: "read_only", INTERNALSECURITY: "read_only", INTERNALHR: "read_only" },
  viewer: { GDPR: "none", SOX: "none", ISO27001: "none", HIPAA: "none", INTERNALSECURITY: "none", INTERNALHR: "none" },
};

// Permission access levels: true | false | "own_dept" | "limited" | "read_only"
const ROLE_PERMISSION_MATRIX = {
  central_admin: { can_view_reports: true, can_download: true, can_export: true, can_delete: true, can_view_pii: true, can_view_financial: true },
  admin: { can_view_reports: true, can_download: true, can_export: true, can_delete: true, can_view_pii: true, can_view_financial: true },
  manager: { can_view_reports: "own_dept", can_download: true, can_export: "own_dept", can_delete: false, can_view_pii: "limited", can_view_financial: "limited" },
  auditor: { can_view_reports: "own_dept", can_download: true, can_export: "own_dept", can_delete: false, can_view_pii: "read_only", can_view_financial: "read_only" },
  viewer: { can_view_reports: "read_only", can_download: false, can_export: false, can_delete: false, can_view_pii: false, can_view_financial: false },
};

function normalizeRoleKey(role) {
  const r = (role || "").toLowerCase().trim();
  if (r === "central_admin" || r === "central admin") return "central_admin";
  if (r === "admin" || r === "department admin" || r === "departmental admin" || r === "department_admin" || r === "departmental_admin") return "admin";
  if (r === "manager") return "manager";
  if (r === "auditor") return "auditor";
  if (r === "viewer") return "viewer";
  return null;
}

function normalizeRegKey(name) {
  return (name || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function getRegAccessLevel(role, regName) {
  const roleKey = normalizeRoleKey(role);
  if (!roleKey) return "full";
  const table = ROLE_REGULATION_MATRIX[roleKey] || {};
  return table[normalizeRegKey(regName)] ?? "none";
}

function getPermAccessLevel(role, permKey) {
  const roleKey = normalizeRoleKey(role);
  if (!roleKey) return true;
  const table = ROLE_PERMISSION_MATRIX[roleKey] || {};
  const level = table[permKey];
  return level === undefined ? false : level;
}

const REG_ACCESS_LABEL = { full: "Full", own_dept: "Own Dept", read_only: "Read Only", none: "Not Permitted" };
const PERM_ACCESS_LABEL = { true: "Full", own_dept: "Own Dept", limited: "Limited", read_only: "Read Only", false: "Not Permitted" };

export default function EnterpriseEmployeeAccessManagement({ token, CAP: incomingCAP }) {
  const CAP = incomingCAP || DEFAULT_CAP;

  const [employees, setEmployees] = useState([]);
  const [selectedEmpId, setSelectedEmpId] = useState("");
  const [currentEmp, setCurrentEmp] = useState(null);

  // Dynamic lookup options from DB
  const [clearanceLevels, setClearanceLevels] = useState([]);
  const [regulations, setRegulations] = useState([]);

  // Editable Form State
  const [clearanceLevelId, setClearanceLevelId] = useState(2);
  const [selectedRegIds, setSelectedRegIds] = useState([]);
  const [permissions, setPermissions] = useState({
    can_view_reports: true,
    can_download: false,
    can_export: false,
    can_delete: false,
    can_view_pii: false,
    can_view_financial: false,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [toastMessage, setToastMessage] = useState("");

  // Logged in user security context
  const loggedUser = JSON.parse(localStorage.getItem("user") || "{}");
  const loggedRole = (loggedUser.role || "viewer").toLowerCase();
  const loggedDept = loggedUser.department || "";

  // Load initial dropdown data from database
  useEffect(() => {
    fetchInitialData();
  }, [token]);

  const fetchInitialData = async () => {
  setLoading(true);
  try {
    const [empRes, clRes, regRes] = await Promise.all([
      apiFetch("/api/v1/employee-access/employees", { token }),
      apiFetch("/api/v1/employee-access/clearance-levels", { token }),
      apiFetch("/api/v1/employee-access/regulations", { token }),
    ]);

    setEmployees(empRes || []);
    setClearanceLevels(clRes || []);
    setRegulations(regRes || []);

    if (empRes && empRes.length > 0) {
      selectEmployee(empRes[0], regRes || []);
    }
  } catch (err) {
    console.error("Failed to load initial ABAC data:", err);
    // No toast shown
  } finally {
    setLoading(false);
  }
};

const showToast = (msg, isError = false) => {
  if (!msg) return;
  setToastMessage({ text: msg, isError });
  setTimeout(() => setToastMessage(""), 5000);
};

const selectEmployee = (emp, regsOverride) => {
  setSelectedEmpId(emp.id);
  setCurrentEmp(emp);
  setClearanceLevelId(emp.clearance_level_id || 2);

  // Clamp stored regulations/permissions down to whatever the employee's
  // role is actually authorized for per the governance matrix — a role
  // change (or stale data) should never leave disallowed grants active.
  // Central Admin and Departmental Admin get every checkbox authorized
  // outright; other roles keep their stored selections, filtered down to
  // what their role permits.
  const regList = regsOverride || regulations;
  const roleKey = normalizeRoleKey(emp.role);
  const isFullAccessRole = roleKey === "central_admin" || roleKey === "admin";

  const rawRegIds = emp.allowed_regulation_ids || [];
  const clampedRegIds = isFullAccessRole
    ? regList.map((r) => r.id)
    : rawRegIds.filter((id) => {
        const reg = regList.find((r) => r.id === id);
        if (!reg) return true; // not loaded yet, don't drop
        return getRegAccessLevel(emp.role, reg.regulation_name) !== "none";
      });
  setSelectedRegIds(clampedRegIds);

  const rawPermissions =
    emp.permissions || {
      can_view_reports: true,
      can_download: false,
      can_export: false,
      can_delete: false,
      can_view_pii: false,
      can_view_financial: false,
    };
  const clampedPermissions = {};
  Object.keys(rawPermissions).forEach((key) => {
    if (isFullAccessRole) {
      clampedPermissions[key] = true;
      return;
    }
    const level = getPermAccessLevel(emp.role, key);
    clampedPermissions[key] = level === false ? false : !!rawPermissions[key];
  });
  setPermissions(clampedPermissions);
};

const handleEmployeeChange = (e) => {
  const id = parseInt(e.target.value, 10);
  const emp = employees.find((item) => item.id === id);
  if (emp) {
    selectEmployee(emp);
  }
};

const toggleRegulation = (regId) => {
  if (!isEditable || !currentEmp) return;

  const reg = regulations.find((r) => r.id === regId);
  const accessLevel = reg ? getRegAccessLevel(currentEmp.role, reg.regulation_name) : "none";
  if (accessLevel === "none") return; // role is not authorized for this regulation at all

  if (selectedRegIds.includes(regId)) {
    setSelectedRegIds(selectedRegIds.filter((id) => id !== regId));
  } else {
    setSelectedRegIds([...selectedRegIds, regId]);
  }
};

const togglePermission = (key) => {
  if (!isEditable || !currentEmp) return;

  const accessLevel = getPermAccessLevel(currentEmp.role, key);
  if (accessLevel === false) return; // role's governance policy blocks this permission outright

  setPermissions((prev) => ({
    ...prev,
    [key]: !prev[key],
  }));
};

const handleSave = async () => {
  if (!currentEmp || !isEditable) return;

  setSaving(true);

  try {
    const payload = {
      clearance_level_id: parseInt(clearanceLevelId, 10),
      allowed_regulation_ids: selectedRegIds,
      permissions,
    };

    const updated = await apiFetch(
      `/api/v1/employee-access/employees/${currentEmp.id}`,
      {
        token,
        method: "PUT",
        body: JSON.stringify(payload),
      }
    );

    if (updated) {
      showToast(`✓ Access attributes updated for ${currentEmp.name}`);

      setEmployees((prev) =>
        prev.map((item) =>
          item.id === currentEmp.id ? { ...item, ...updated } : item
        )
      );

      selectEmployee({ ...currentEmp, ...updated });
    }
  } catch (err) {
    console.error("Save failed:", err);
    // Do NOT show any error popup
    // showToast(err.message || "Failed to update employee attributes", true);
  } finally {
    setSaving(false);
  }
};
  // Determine security edit restrictions
  let isEditable = false;
  let editRestrictionReason = "";

  if (currentEmp) {
    const targetDept = currentEmp.department || "";
    const targetRole = (currentEmp.role || "").toLowerCase();

    if (loggedRole === "central_admin") {
      // Central Admin sits at the top of the hierarchy and can manage every
      // employee, including other Central Admins / Departmental Admins.
      isEditable = true;
    } else if (loggedRole === "admin" || loggedRole === "manager" || loggedRole === "department admin") {
      if (loggedDept && targetDept && loggedDept.toLowerCase() !== targetDept.toLowerCase()) {
        isEditable = false;
        editRestrictionReason = `Department boundary restriction: You can only manage employees within '${loggedDept}'. Target is in '${targetDept}'.`;
      } else if (["central_admin", "admin", "manager", "department admin"].includes(targetRole)) {
        isEditable = false;
        editRestrictionReason = `Privilege escalation prevention: Cannot modify access attributes for administrative role '${currentEmp.role}'.`;
      } else {
        isEditable = true;
      }
    } else {
      isEditable = false;
      editRestrictionReason = "Central Admin or Department Manager permissions required to edit employee access attributes.";
    }
  }

  const filteredEmployees = employees.filter(
    (e) =>
      e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (e.department && e.department.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const selectedClearanceObj = clearanceLevels.find((c) => c.id === parseInt(clearanceLevelId, 10));

  if (loading) {
    return (
      <div style={{ padding: 48, textAlign: "center", color: CAP.textDim }}>
        <Sparkles size={32} color={CAP.purple} style={{ animation: "spin 2s linear infinite", marginBottom: 14 }} />
        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, color: CAP.text }}>
          Loading Enterprise Access Attributes…
        </div>
        <div style={{ fontSize: 13, color: CAP.textFaint, marginTop: 6 }}>
          Syncing clearance levels, regulations, and employee RBAC rules from database
        </div>
      </div>
    );
  }

  const PERMISSION_CONFIGS = [
    { key: "can_view_reports", label: "View Audit Reports", icon: Eye, desc: "Access scan records & dashboards" },
    { key: "can_download", label: "Download Reports", icon: Download, desc: "Download PDF & audit workpapers" },
    { key: "can_export", label: "Export Data", icon: FileSpreadsheet, desc: "Export CSV/JSON compliance metrics" },
    { key: "can_delete", label: "Delete Records", icon: Trash2, desc: "Purge audit logs & scan history" },
    { key: "can_view_pii", label: "View PII Data", icon: Fingerprint, desc: "Unmask emails, phones, and SSNs" },
    { key: "can_view_financial", label: "View Financial Data", icon: DollarSign, desc: "Access fine exposure & salary details" },
  ];

  return (
    <div style={{ minWidth: 0, width: "100%" }}>
      {/* ─── HEADER BANNER ─── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ color: CAP.purple, fontSize: 11.5, fontWeight: 700, letterSpacing: "0.14em", textTransform: "uppercase" }}>
          SECURITY & GOVERNANCE • ABAC POLICY ENGINE
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16, marginTop: 4 }}>
          <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 32, fontWeight: 700, color: CAP.text, margin: 0 }}>
            Enterprise Employee Access Management
          </h1>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 14px",
              borderRadius: 99,
              background: "rgba(201, 169, 110, 0.12)",
              border: `1px solid ${CAP.borderBt}`,
              color: CAP.purpleDark,
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            <ShieldCheck size={15} color={CAP.purple} />
            <span>Active Session Context: {loggedRole.toUpperCase()} ({loggedDept || "Global"})</span>
          </div>
        </div>
        <p style={{ color: CAP.textDim, fontSize: 13.5, marginTop: 6, maxWidth: 840, lineHeight: 1.55 }}>
          Configure fine-grained Attribute-Based Access Control (ABAC) attributes, security clearance tiers, statutory regulation permissions, and data-masking rules synced directly to the PostgreSQL/SQLite database.
        </p>
      </div>

      {/* ─── TOAST NOTIFICATION ─── */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            style={{
              padding: "12px 20px",
              backgroundColor: toastMessage.isError ? "rgba(184, 92, 56, 0.12)" : "rgba(90, 122, 106, 0.12)",
              border: `1px solid ${toastMessage.isError ? CAP.red : CAP.green}`,
              borderRadius: 14,
              color: toastMessage.isError ? CAP.red : CAP.green,
              marginBottom: 24,
              fontSize: 13.5,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              backdropFilter: "blur(12px)",
              boxShadow: "0 10px 30px -10px rgba(0,0,0,0.06)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {toastMessage.isError ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
              <span>{toastMessage.text}</span>
            </div>
            <button
              onClick={() => setToastMessage("")}
              style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: 4 }}
            >
              <X size={15} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── MAIN TWO-COLUMN GRID ─── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.75fr", gap: 24, alignItems: "flex-start" }}>
        
        {/* ─── LEFT COLUMN: SELECTION & READ-ONLY CONTEXT ─── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          
          {/* Card 1: Employee Selection */}
          <div
            style={{
              background: CAP.panel,
              border: `1px solid ${CAP.border}`,
              borderRadius: 20,
              padding: 22,
              boxShadow: "0 24px 60px -22px rgba(20, 33, 61, 0.10)",
              backdropFilter: "blur(20px)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <UserCheck size={18} color={CAP.purple} />
              <h3 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 19, fontWeight: 700, color: CAP.text, margin: 0 }}>
                1. Target Employee Selection
              </h3>
            </div>

            <div style={{ position: "relative", marginBottom: 14 }}>
              <Search size={15} color={CAP.textFaint} style={{ position: "absolute", left: 12, top: 11 }} />
              <input
                type="text"
                placeholder="Search by name, email or department…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "9px 12px 9px 36px",
                  borderRadius: 12,
                  border: `1px solid ${CAP.border}`,
                  backgroundColor: "rgba(20, 33, 61, 0.02)",
                  color: CAP.text,
                  fontSize: 13,
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <label style={{ fontSize: 11, color: CAP.textFaint, fontWeight: 700, letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
              SELECT EMPLOYEE RECORD ({filteredEmployees.length} FOUND)
            </label>
            <select
              value={selectedEmpId}
              onChange={handleEmployeeChange}
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: 12,
                border: `1px solid ${CAP.purple}60`,
                backgroundColor: "#FFFFFF",
                color: CAP.text,
                fontSize: 13.5,
                fontWeight: 600,
                cursor: "pointer",
                outline: "none",
                boxShadow: "0 2px 10px rgba(0,0,0,0.03)",
              }}
            >
              {filteredEmployees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name} ({emp.department} • {emp.role})
                </option>
              ))}
            </select>
          </div>

          {/* Card 2: Employee Profile Context */}
          {currentEmp && (
            <div
              style={{
                background: CAP.panel,
                border: `1px solid ${CAP.border}`,
                borderRadius: 20,
                padding: 22,
                boxShadow: "0 24px 60px -22px rgba(20, 33, 61, 0.10)",
                backdropFilter: "blur(20px)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Building2 size={18} color={CAP.purple} />
                  <h3 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 19, fontWeight: 700, color: CAP.text, margin: 0 }}>
                    2. Employee Metadata Profile
                  </h3>
                </div>
                <span
                  style={{
                    fontSize: 10.5,
                    fontFamily: "'JetBrains Mono', monospace",
                    backgroundColor: "rgba(20, 33, 61, 0.05)",
                    color: CAP.textFaint,
                    padding: "3px 9px",
                    borderRadius: 99,
                    fontWeight: 700,
                    border: `1px solid ${CAP.border}`,
                  }}
                >
                  DATABASE READ-ONLY
                </span>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 14, paddingBottom: 16, marginBottom: 14, borderBottom: `1px solid ${CAP.border}` }}>
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 14,
                    background: `linear-gradient(135deg, ${CAP.purple}, ${CAP.purpleDark})`,
                    display: "grid",
                    placeItems: "center",
                    color: "#fff",
                    fontWeight: 700,
                    fontSize: 18,
                    flexShrink: 0,
                    boxShadow: `0 0 15px ${CAP.purpleGlow}`,
                  }}
                >
                  {currentEmp.name ? currentEmp.name.charAt(0) : "E"}
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: CAP.text }}>{currentEmp.name}</div>
                  <div style={{ fontSize: 12.5, color: CAP.textDim }}>{currentEmp.email}</div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                <div>
                  <div style={{ fontSize: 10.5, color: CAP.textFaint, textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.06em" }}>
                    EMPLOYEE ID
                  </div>
                  <div style={{ fontSize: 13, color: CAP.purple, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, marginTop: 2 }}>
                    {currentEmp.employee_id || `EMP-${currentEmp.id}`}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10.5, color: CAP.textFaint, textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.06em" }}>
                    DEPARTMENT
                  </div>
                  <div style={{ fontSize: 13.5, color: CAP.text, fontWeight: 600, marginTop: 2 }}>
                    {currentEmp.department || "General"}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10.5, color: CAP.textFaint, textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.06em" }}>
                    ASSIGNED ROLE
                  </div>
                  <div style={{ fontSize: 13, color: CAP.cyan, fontWeight: 700, marginTop: 2 }}>
                    {currentEmp.role}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 10.5, color: CAP.textFaint, textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.06em" }}>
                    CLEARANCE TIER
                  </div>
                  <div style={{ fontSize: 13, color: CAP.teal, fontWeight: 700, marginTop: 2 }}>
                    {selectedClearanceObj ? selectedClearanceObj.clearance_name : `Rank ${clearanceLevelId}`}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Card 3: Effective Access Live Radar Preview */}
          <div
            style={{
              background: "rgba(201, 169, 110, 0.04)",
              border: `1px dashed ${CAP.borderBt}`,
              borderRadius: 20,
              padding: 22,
              backdropFilter: "blur(20px)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <KeyRound size={17} color={CAP.purple} />
              <h4 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 18, fontWeight: 700, color: CAP.purpleDark, margin: 0 }}>
                Effective Access Live Radar
              </h4>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: CAP.textDim }}>Active Clearance:</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: CAP.purple, fontSize: 12.5 }}>
                  {selectedClearanceObj ? selectedClearanceObj.clearance_name : "Internal"}
                </span>
              </div>

              <div>
                <span style={{ color: CAP.textDim, fontSize: 12.5, fontWeight: 600, display: "block", marginBottom: 6 }}>
                  Statutory Regulations Authorized:
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {selectedRegIds.length === 0 ? (
                    <span style={{ color: CAP.textFaint, fontSize: 12, fontStyle: "italic" }}>No statutory regulations assigned</span>
                  ) : (
                    selectedRegIds.map((id) => {
                      const r = regulations.find((reg) => reg.id === id);
                      return (
                        <span
                          key={id}
                          style={{
                            background: "rgba(90, 122, 106, 0.12)",
                            color: CAP.green,
                            border: `1px solid ${CAP.green}40`,
                            padding: "3px 9px",
                            borderRadius: 99,
                            fontSize: 11,
                            fontWeight: 700,
                          }}
                        >
                          ✓ {r ? r.regulation_name : id}
                        </span>
                      );
                    })
                  )}
                </div>
              </div>

              <div style={{ borderTop: `1px solid ${CAP.border}`, paddingTop: 10, marginTop: 4, display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ fontSize: 11, color: CAP.textFaint, fontWeight: 700, letterSpacing: "0.06em", marginBottom: 2 }}>
                  LIVE PERMISSIONS AUDIT
                </div>
                {PERMISSION_CONFIGS.map((item) => {
                  const isOn = permissions[item.key];
                  return (
                    <div key={item.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
                      <span style={{ color: CAP.textDim }}>{item.label}</span>
                      {isOn ? (
                        <span style={{ color: CAP.green, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11.5 }}>
                          <Check size={13} /> Granted
                        </span>
                      ) : (
                        <span style={{ color: CAP.red, fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11.5, opacity: 0.75 }}>
                          <X size={13} /> Masked
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

        </div>

        {/* ─── RIGHT COLUMN: ACCESS ATTRIBUTES CONTROL CENTER ─── */}
        <div
          style={{
            background: CAP.panel,
            border: `1px solid ${CAP.border}`,
            borderRadius: 20,
            padding: 26,
            boxShadow: "0 24px 60px -22px rgba(20, 33, 61, 0.10)",
            backdropFilter: "blur(20px)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, paddingBottom: 14, borderBottom: `1px solid ${CAP.border}` }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Sliders size={20} color={CAP.purple} />
                  <h3 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, fontWeight: 700, color: CAP.text, margin: 0 }}>
                    3. Access Attributes Control Center
                  </h3>
                </div>
                <div style={{ fontSize: 12.5, color: CAP.textDim, marginTop: 3 }}>
                  Modify employee clearance level, assigned regulations, and operational permissions.
                </div>
              </div>
              <span
                style={{
                  padding: "6px 14px",
                  borderRadius: 99,
                  fontSize: 11.5,
                  fontWeight: 700,
                  background: isEditable ? "rgba(90, 122, 106, 0.12)" : "rgba(201, 169, 110, 0.12)",
                  color: isEditable ? CAP.green : CAP.amber,
                  border: `1px solid ${isEditable ? CAP.green + "40" : CAP.amber + "40"}`,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                {isEditable ? <CheckCircle2 size={14} /> : <Lock size={14} />}
                {isEditable ? "Editable Mode" : "Read-Only Mode"}
              </span>
            </div>

            {/* Security Guardrail Callout */}
            {!isEditable && editRestrictionReason && (
              <div
                style={{
                  padding: "14px 18px",
                  backgroundColor: "rgba(201, 169, 110, 0.08)",
                  border: `1px solid ${CAP.borderBt}`,
                  borderRadius: 14,
                  color: CAP.text,
                  fontSize: 13,
                  lineHeight: 1.5,
                  marginBottom: 24,
                  display: "flex",
                  gap: 12,
                  alignItems: "flex-start",
                }}
              >
                <Lock size={18} color={CAP.purple} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <strong style={{ color: CAP.purpleDark, display: "block", marginBottom: 2 }}>
                    Authorization Policy Restriction:
                  </strong>
                  <span style={{ color: CAP.textDim }}>{editRestrictionReason}</span>
                </div>
              </div>
            )}

            {/* SECTION A: Clearance Level */}
            

            {/* SECTION B: Allowed Regulations */}
            <div style={{ marginBottom: 28 }}>
              <label style={{ fontSize: 13, fontWeight: 700, color: CAP.text, display: "block", marginBottom: 8 }}>
                STATUTORY REGULATION AUTHORIZATIONS
              </label>
              <div style={{ fontSize: 12, color: CAP.textFaint, marginBottom: 12 }}>
                Select regulatory frameworks this employee is authorized to review and handle.
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 10 }}>
                {regulations.map((reg) => {
                  const isChecked = selectedRegIds.includes(reg.id);
                  const accessLevel = currentEmp ? getRegAccessLevel(currentEmp.role, reg.regulation_name) : "full";
                  const isBlocked = accessLevel === "none";
                  const clickable = isEditable && !isBlocked;
                  return (
                    <div
                      key={reg.id}
                      onClick={() => toggleRegulation(reg.id)}
                      title={isBlocked ? `Not permitted for role '${currentEmp?.role}' per governance policy` : REG_ACCESS_LABEL[accessLevel]}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "11px 14px",
                        backgroundColor: isBlocked ? "rgba(20, 33, 61, 0.03)" : isChecked ? "rgba(201, 169, 110, 0.10)" : "#FFFFFF",
                        border: `1px solid ${isBlocked ? CAP.border : isChecked ? CAP.purple : CAP.border}`,
                        borderRadius: 12,
                        cursor: clickable ? "pointer" : "not-allowed",
                        color: isBlocked ? CAP.textFaint : isChecked ? CAP.purpleDark : CAP.textDim,
                        fontSize: 13,
                        fontWeight: isChecked ? 700 : 500,
                        userSelect: "none",
                        transition: "all 0.2s ease",
                        opacity: isBlocked ? 0.55 : 1,
                        position: "relative",
                      }}
                    >
                      <div
                        style={{
                          width: 18,
                          height: 18,
                          borderRadius: 6,
                          border: `1.5px solid ${isBlocked ? CAP.textFaint : isChecked ? CAP.purple : CAP.textFaint}`,
                          background: isChecked && !isBlocked ? CAP.purple : "transparent",
                          display: "grid",
                          placeItems: "center",
                          color: "#fff",
                          flexShrink: 0,
                        }}
                      >
                        {isBlocked ? (
                          <Lock size={10} color={CAP.textFaint} />
                        ) : (
                          isChecked && <Check size={12} strokeWidth={3} />
                        )}
                      </div>
                      <span style={{ flex: 1, minWidth: 0 }}>{reg.regulation_name}</span>
                      {!isBlocked && accessLevel !== "full" && (
                        <span
                          style={{
                            fontSize: 9,
                            fontWeight: 800,
                            letterSpacing: "0.04em",
                            color: CAP.cyan,
                            background: CAP.cyanGlow,
                            padding: "2px 6px",
                            borderRadius: 99,
                            flexShrink: 0,
                          }}
                        >
                          {REG_ACCESS_LABEL[accessLevel].toUpperCase()}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              {currentEmp && (
                <div style={{ fontSize: 11, color: CAP.textFaint, marginTop: 10, display: "flex", alignItems: "center", gap: 6 }}>
                  <ShieldCheck size={12} color={CAP.textFaint} />
                  Governed by role &quot;{currentEmp.role}&quot; per the Statutory Regulation Authorizations policy. Greyed-out, locked entries are not permitted for this role.
                </div>
              )}
            </div>

            {/* SECTION C: Fine-Grained Permissions */}
            <div style={{ marginBottom: 28 }}>
              <label style={{ fontSize: 13, fontWeight: 700, color: CAP.text, display: "block", marginBottom: 8 }}>
                FINE-GRAINED OPERATIONAL PERMISSIONS
              </label>
              <div style={{ fontSize: 12, color: CAP.textFaint, marginBottom: 14 }}>
                Toggle granular feature flags and data masking protections for this employee.
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {PERMISSION_CONFIGS.map((item) => {
                  const Icon = item.icon;
                  const isOn = permissions[item.key];
                  const accessLevel = currentEmp ? getPermAccessLevel(currentEmp.role, item.key) : true;
                  const isBlocked = accessLevel === false;
                  const canToggle = isEditable && !isBlocked;
                  const badgeText = !isBlocked && accessLevel !== true ? PERM_ACCESS_LABEL[accessLevel] : null;
                  return (
                    <div
                      key={item.key}
                      title={isBlocked ? `Not permitted for role '${currentEmp?.role}' per governance policy` : undefined}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "12px 14px",
                        backgroundColor: isBlocked ? "rgba(20, 33, 61, 0.03)" : isOn ? "rgba(90, 122, 106, 0.05)" : "rgba(20, 33, 61, 0.02)",
                        borderRadius: 14,
                        border: `1px solid ${isBlocked ? CAP.border : isOn ? CAP.green + "35" : CAP.border}`,
                        transition: "all 0.2s ease",
                        opacity: isBlocked ? 0.55 : 1,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 10,
                            background: isOn && !isBlocked ? "rgba(90, 122, 106, 0.12)" : "rgba(20, 33, 61, 0.04)",
                            display: "grid",
                            placeItems: "center",
                            color: isOn && !isBlocked ? CAP.green : CAP.textFaint,
                            flexShrink: 0,
                          }}
                        >
                          {isBlocked ? <Lock size={14} /> : <Icon size={16} />}
                        </div>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: 12.5, fontWeight: 700, color: CAP.text, display: "flex", alignItems: "center", gap: 6 }}>
                            {item.label}
                            {badgeText && (
                              <span
                                style={{
                                  fontSize: 9,
                                  fontWeight: 800,
                                  letterSpacing: "0.04em",
                                  color: CAP.cyan,
                                  background: CAP.cyanGlow,
                                  padding: "2px 6px",
                                  borderRadius: 99,
                                }}
                              >
                                {badgeText.toUpperCase()}
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: 10.5, color: CAP.textFaint, textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                            {isBlocked ? `Blocked by governance policy for '${currentEmp?.role}'` : item.desc}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        disabled={!canToggle}
                        onClick={() => togglePermission(item.key)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: 99,
                          border: "none",
                          backgroundColor: isOn && !isBlocked
                            ? `linear-gradient(135deg, ${CAP.green}, #22c55e)`
                            : "rgba(20, 33, 61, 0.10)",
                          background: isBlocked ? "rgba(22, 18, 14, 0.08)" : isOn ? CAP.green : "rgba(22, 18, 14, 0.12)",
                          color: isOn && !isBlocked ? "#FFFFFF" : CAP.textFaint,
                          fontSize: 11.5,
                          fontWeight: 800,
                          letterSpacing: "0.04em",
                          cursor: canToggle ? "pointer" : "not-allowed",
                          transition: "all 0.2s ease",
                          flexShrink: 0,
                          marginLeft: 8,
                          boxShadow: isOn && !isBlocked ? `0 0 12px ${CAP.green}30` : "none",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        {isBlocked ? (
                          <>
                            <Lock size={10} /> LOCKED
                          </>
                        ) : isOn ? (
                          "ENABLED"
                        ) : (
                          "OFF"
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
              {currentEmp && (
                <div style={{ fontSize: 11, color: CAP.textFaint, marginTop: 10, display: "flex", alignItems: "center", gap: 6 }}>
                  <ShieldCheck size={12} color={CAP.textFaint} />
                  Governed by role &quot;{currentEmp.role}&quot; per the Feature Access policy. Locked toggles cannot be enabled for this role.
                </div>
              )}
            </div>
          </div>

          {/* SAVE BUTTON */}
          <div style={{ paddingTop: 20, borderTop: `1px solid ${CAP.border}` }}>
            <button
              onClick={handleSave}
              disabled={saving || !isEditable}
              style={{
                width: "100%",
                padding: "14px 22px",
                borderRadius: 14,
                border: "none",
                background: !isEditable
                  ? "rgba(20, 33, 61, 0.10)"
                  : `linear-gradient(135deg, ${CAP.purple}, ${CAP.purpleDark})`,
                color: !isEditable ? CAP.textFaint : "#FFFFFF",
                fontSize: 14,
                fontWeight: 700,
                cursor: !isEditable || saving ? "not-allowed" : "pointer",
                boxShadow: isEditable ? `0 10px 25px -8px ${CAP.purpleGlow}` : "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
                transition: "all 0.2s ease",
              }}
            >
              {saving ? (
                <>
                  <Sparkles size={16} style={{ animation: "spin 1s linear infinite" }} />
                  Saving Changes to Database…
                </>
              ) : !isEditable ? (
                <>
                  <Lock size={16} />
                  Authorization Guarded (Editing Disabled for Target)
                </>
              ) : (
                <>
                  <Save size={16} />
                  Save Employee Access Attributes
                </>
              )}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
