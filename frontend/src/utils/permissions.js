export const PERMISSIONS = {
  central_admin: [
    "dashboard",
    "upload",
    "scan",
    "users",
    "reports",
    "audit",
    "policy_create",
    "policy_delete",
    "policy_edit",
    "remediation",
    "simulator",
    "report_delete",
    "view",
  ],

  manager: [
    "dashboard",
    "reports",
    "audit",
    "policy_create",
    "policy_edit",
    "simulator",
    "upload",
    "scan",
    "view"
  ],

  auditor: [
    "dashboard",
    "reports",
    "audit",
    "view"
  ],

  viewer: [
    "dashboard",
    "view",
  ],

  admin: [
    "dashboard",
    "upload",
    "scan",
    "users",
    "reports",
    "audit",
    "policy_create",
    "policy_edit",
    "remediation",
    "simulator",
    "report_delete",
    "view"
  ],
};

export function hasPermission(role, permission) {
  return PERMISSIONS[role]?.includes(permission) ?? false;
}