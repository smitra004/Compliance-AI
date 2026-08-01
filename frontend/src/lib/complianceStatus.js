// Single source of truth for turning a compliance_score into a status,
// risk level, and color anywhere in the UI (Audit Desk, Dashboard, Reports,
// badges, filters, downloaded report views). Never derive status from
// violation counts or severity — always from the score.
//
//   80-100 -> Compliant        (green)
//   60-79  -> Partially Compliant / Needs Remediation (amber)
//   0-59   -> Non-Compliant    (red)

// Colors mirror the CAP palette defined in AppFull.jsx (kept in sync
// manually since CAP itself isn't exported as a shared module).
const COLORS = {
  green: "#5A7A6A",
  amber: "#C9A96E",
  red: "#B85C38",
};

export function getComplianceStatus(score) {
  if (score >= 80) {
    return { key: "compliant", label: "Compliant", short: "COMPLIANT" };
  }
  if (score >= 60) {
    return {
      key: "partial",
      label: "Partially Compliant",
      short: "NEEDS REMEDIATION",
    };
  }
  return { key: "non_compliant", label: "Non-Compliant", short: "NON-COMPLIANT" };
}

export function getRiskLevel(score) {
  if (score >= 80) return "Low";
  if (score >= 60) return "Medium";
  return "High";
}

export function getComplianceColor(score) {
  if (score >= 80) return COLORS.green;
  if (score >= 60) return COLORS.amber;
  return COLORS.red;
}
