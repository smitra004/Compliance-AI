import React, { useState, useEffect } from "react";
import { ShieldCheck, UserCheck, Sliders, Activity, Layers, FileText, Lock, Zap } from "lucide-react";

import GovernanceDashboard from "./GovernanceDashboard";
import ProductionUserPortal from "./ProductionUserPortal";
import PolicySandbox from "./PolicySandbox";
import EnterprisePolicyRegistry from "./EnterprisePolicyRegistry";
import DecisionPipeline from "./DecisionPipeline";
import RiskBreakdown from "./RiskBreakdown";
import AttributeInspector from "./AttributeInspector";
import ConflictResolution from "./ConflictResolution";
import DataMaskingEngine from "./DataMaskingEngine";
import AuditInvestigation from "./AuditInvestigation";
import OPAViewer from "./OPAViewer";

export default function ABACGovernance({ token, CAP }) {
  // Top Mode: 'production' vs 'admin'
  const [portalMode, setPortalMode] = useState("production");
  const [adminTab, setAdminTab] = useState("dashboard");

  // Shared State
  const [modeData, setModeData] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [opaBundle, setOpaBundle] = useState(null);
  const [reloadStatus, setReloadStatus] = useState("");

  // Admin Sandbox Inputs
  const [user, setUser] = useState("admin");
  const [role, setRole] = useState("manager");
  const [department, setDepartment] = useState("Finance");
  const [action, setAction] = useState("Read");
  const [clearanceLevel, setClearanceLevel] = useState("Confidential");
  const [mfaStatus, setMfaStatus] = useState(true);
  const [vpnConnected, setVpnConnected] = useState(true);
  const [businessHours, setBusinessHours] = useState(true);
  const [classification, setClassification] = useState("Confidential");
  const [containsPii, setContainsPii] = useState(true);
  const [containsFin, setContainsFin] = useState(true);
  const [country, setCountry] = useState("US");

  // Live User Management roster (real users, no mock/sample data)
  const [realUsers, setRealUsers] = useState([]);
  const [evalResult, setEvalResult] = useState(null);
  const [evalResource, setEvalResource] = useState(null);
  const [loading, setLoading] = useState(false);

  const authToken = token || localStorage.getItem("token") || "";

  // 1. Fetch Mode Data
  const fetchMode = async () => {
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      const res = await fetch("/api/v1/abac/mode", { headers });
      const data = await res.json();
      setModeData(data);
    } catch (err) {
      console.error("Fetch mode error:", err);
    }
  };

  // 2. Fetch Policies
  const fetchPolicies = async () => {
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      const res = await fetch("/api/v1/abac/policies", { headers });
      const data = await res.json();
      if (Array.isArray(data)) setPolicies(data);
    } catch (err) {
      console.error("Fetch policies error:", err);
    }
  };

  // 3. Fetch OPA Bundle
  const fetchOpaBundle = async () => {
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      const res = await fetch("/api/v1/abac/opa-bundle", { headers });
      const data = await res.json();
      setOpaBundle(data);
    } catch (err) {
      console.error("Fetch OPA bundle error:", err);
    }
  };

  // 3b. Fetch real users from User Management (no mock/sample data)
  const fetchUsers = async () => {
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      const res = await fetch("/api/v1/abac/users", { headers });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setRealUsers(data);
      }
    } catch (err) {
      console.error("Fetch users error:", err);
    }
  };

  // 4. Run Admin Simulation
  const runSimulation = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/abac/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authToken ? `Bearer ${authToken}` : "",
        },
        body: JSON.stringify({
          user,
          role,
          department,
          action,
          subject: {
            clearance_level: clearanceLevel,
            mfa_status: mfaStatus,
          },
          resource: {
            department,
            classification,
            contains_pii: containsPii,
            contains_financial_data: containsFin,
          },
          environment: {
            vpn_connected: vpnConnected,
            business_hours: businessHours,
            country,
          },
        }),
      });
      const data = await res.json();
      setEvalResult(data);
    } catch (err) {
      console.error("ABAC Simulation error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (policyId, targetStatus) => {
    try {
      const headers = {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      };
      await fetch(`/api/v1/abac/policies/${policyId}/status`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ status: targetStatus }),
      });
      fetchPolicies();
    } catch (err) {
      console.error("Status update error:", err);
    }
  };

  const handleReloadPolicies = async () => {
    setReloadStatus("Reloading...");
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};
      const res = await fetch("/api/v1/abac/reload-policies", {
        method: "POST",
        headers,
      });
      const data = await res.json();
      setReloadStatus(`Reloaded ${data.total_policies} policies!`);
      fetchPolicies();
      setTimeout(() => setReloadStatus(""), 3000);
    } catch (err) {
      setReloadStatus("Reload failed.");
    }
  };

  useEffect(() => {
    fetchMode();
    fetchPolicies();
    fetchOpaBundle();
    fetchUsers();
    runSimulation();
  }, []);

  const handleProdEvalComplete = (resultData, resourceObj) => {
    setEvalResult(resultData);
    setEvalResource(resourceObj);
  };

  const styles = {
    card: {
      background: CAP?.panel || "#FFFFFF",
      border: `1px solid ${CAP?.border || "rgba(0,0,0,0.08)"}`,
      borderRadius: 14,
      padding: 20,
      boxShadow: "0 4px 20px rgba(0,0,0,0.03)",
      marginBottom: 20,
    },
  };

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto" }}>
      {/* Top Header & Dual Mode Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <div style={{ padding: 10, borderRadius: 12, background: "rgba(201, 169, 110, 0.15)", color: CAP?.purple || "#C9A96E" }}>
              <ShieldCheck size={24} />
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, color: CAP?.text }}>
              Master Production-Grade Enterprise ABAC Governance Platform
            </h1>
          </div>
          <p style={{ margin: 0, color: CAP?.textDim, fontSize: 13 }}>
            NIST SP 800-162 & Zero Trust Architecture · JWT IdP Claims → RBAC → Central Clearance → Risk Engine → Field Masking → Audit
          </p>
        </div>

        <div style={{ display: "flex", background: CAP?.bg, padding: 4, borderRadius: 12, border: `1px solid ${CAP?.purple || "#C9A96E"}` }}>
          <button
            onClick={() => setPortalMode("production")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "9px 16px",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: portalMode === "production" ? CAP?.purple || "#C9A96E" : "transparent",
              color: portalMode === "production" ? "#16120E" : CAP?.textDim,
            }}
          >
            <UserCheck size={16} /> Production User Portal (Employee View)
          </button>
          <button
            onClick={() => setPortalMode("admin")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "9px 16px",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              background: portalMode === "admin" ? CAP?.panel : "transparent",
              color: portalMode === "admin" ? CAP?.text : CAP?.textDim,
            }}
          >
            <Sliders size={16} /> Administrator Policy Sandbox (Simulator View)
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 🏢 PORTAL MODE 1: PRODUCTION USER PORTAL (EMPLOYEE VIEW)                  */}
      {/* ========================================================================= */}
      {portalMode === "production" && (
        <div>
          <ProductionUserPortal
            token={token}
            CAP={CAP}
            modeData={modeData}
            onEvalComplete={handleProdEvalComplete}
          />

          {/* Connected Evaluation Output Components */}
          {evalResult && (
            <div>
              <RiskBreakdown
                CAP={CAP}
                riskScore={evalResult.risk_score}
                riskLevel={evalResult.risk_level}
                riskBreakdown={evalResult.risk_breakdown}
              />

              <AttributeInspector CAP={CAP} evalData={evalResult} />

              <ConflictResolution CAP={CAP} evalData={evalResult} />

              <DataMaskingEngine
                CAP={CAP}
                rawContent={evalResult.raw_content}
                maskedContent={evalResult.masked_content}
                obligations={evalResult.obligations}
              />

              <DecisionPipeline
                CAP={CAP}
                pipelineData={evalResult.pipeline_visualization}
                executionTimeMs={evalResult.execution_time_ms}
              />
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ⚙️ PORTAL MODE 2: ADMINISTRATOR POLICY SANDBOX (SIMULATOR VIEW)          */}
      {/* ========================================================================= */}
      {portalMode === "admin" && (
        <div>
          {/* Admin Navigation Tabs */}
          <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
            {[
              { id: "dashboard", label: "Governance Dashboard", icon: <Activity size={15} /> },
              { id: "sandbox", label: "Policy Testing Sandbox", icon: <Sliders size={15} /> },
              { id: "registry", label: "Enterprise Policy Registry", icon: <Layers size={15} /> },
              { id: "opa", label: "CNCF OPA Rego Generator", icon: <FileText size={15} /> },
              { id: "masking", label: "Data Masking Engine", icon: <Lock size={15} /> },
              { id: "audit", label: "Forensic Audit Investigation", icon: <ShieldCheck size={15} /> },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setAdminTab(t.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: `1px solid ${adminTab === t.id ? CAP?.purple || "#C9A96E" : CAP?.border}`,
                  background: adminTab === t.id ? CAP?.panel : CAP?.bg,
                  color: adminTab === t.id ? CAP?.text : CAP?.textDim,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {adminTab === "dashboard" && <GovernanceDashboard token={token} CAP={CAP} />}

          {adminTab === "sandbox" && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <PolicySandbox
                CAP={CAP}
                realUsers={realUsers}
                user={user} setUser={setUser}
                role={role} setRole={setRole}
                department={department} setDepartment={setDepartment}
                action={action} setAction={setAction}
                clearanceLevel={clearanceLevel} setClearanceLevel={setClearanceLevel}
                mfaStatus={mfaStatus} setMfaStatus={setMfaStatus}
                vpnConnected={vpnConnected} setVpnConnected={setVpnConnected}
                businessHours={businessHours} setBusinessHours={setBusinessHours}
                classification={classification} setClassification={setClassification}
                containsPii={containsPii} setContainsPii={setContainsPii}
                containsFin={containsFin} setContainsFin={setContainsFin}
                country={country} setCountry={setCountry}
                loading={loading}
                runSimulation={runSimulation}
              />

              {evalResult && (
                <div>
                  <RiskBreakdown
                    CAP={CAP}
                    riskScore={evalResult.risk_score}
                    riskLevel={evalResult.risk_level}
                    riskBreakdown={evalResult.risk_breakdown}
                  />
                  <AttributeInspector CAP={CAP} evalData={evalResult} />
                  <ConflictResolution CAP={CAP} evalData={evalResult} />
                  <DecisionPipeline CAP={CAP} pipelineData={evalResult.pipeline_visualization} executionTimeMs={evalResult.execution_time_ms} />
                </div>
              )}
            </div>
          )}

          {adminTab === "registry" && (
            <EnterprisePolicyRegistry
              CAP={CAP}
              policies={policies}
              fetchPolicies={fetchPolicies}
              handleStatusChange={handleStatusChange}
              reloadStatus={reloadStatus}
              handleReloadPolicies={handleReloadPolicies}
            />
          )}

          {adminTab === "opa" && <OPAViewer CAP={CAP} opaBundle={opaBundle} />}

          {adminTab === "masking" && (
            <DataMaskingEngine
              CAP={CAP}
              rawContent={evalResult?.raw_content}
              maskedContent={evalResult?.masked_content}
              obligations={evalResult?.obligations}
            />
          )}

          {adminTab === "audit" && <AuditInvestigation token={token} CAP={CAP} />}
        </div>
      )}
    </div>
  );
}
