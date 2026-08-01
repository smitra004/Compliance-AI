import { useState } from "react";
import {
  ShieldCheck,
  Lock,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

const BASE = "/api";

const C = {
  bg: "#FAF7F2",
  bgGradient: "radial-gradient(1200px 720px at 12% -12%, #F3EEE2 0%, #FAF7F2 58%)",
  panel: "#FFFFFF",
  border: "rgba(22,18,14,0.09)",
  text: "#16120E",
  textDim: "#5C5248",
  textFaint: "#8C8278",
  gold: "#C9A96E",
  goldDark: "#B8923A",
  goldGlow: "rgba(201,169,110,0.16)",
  green: "#5A7A6A",
  red: "#B85C38",
};

export default function ChangePassword({ user, onSuccess }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const checks = {
    length: newPassword.length >= 8,
    uppercase: /[A-Z]/.test(newPassword),
    lowercase: /[a-z]/.test(newPassword),
    number: /\d/.test(newPassword),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword),
  };

  const valid =
    checks.length &&
    checks.uppercase &&
    checks.lowercase &&
    checks.number &&
    checks.special;

  async function changePassword() {
    setError("");
    setSuccess("");

    if (!currentPassword) {
      setError("Please enter your temporary password.");
      return;
    }

    if (!valid) {
      setError("Password does not meet security requirements.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);

      const token = localStorage.getItem("token");

      const r = await fetch(`${BASE}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            old_password: currentPassword,
            new_password: newPassword,
        }),
      });

      const data = await r.json();

      if (!r.ok) {
        throw new Error(data.detail || "Unable to change password");
      }

      setSuccess("Password updated successfully.");

      const updatedUser = {
        ...user,
        mustChangePassword: false,
      };

      localStorage.removeItem("forcePasswordChange");
      localStorage.setItem("user", JSON.stringify(updatedUser));

      setTimeout(() => {
        onSuccess(updatedUser);
      }, 1200);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: C.bgGradient,
        padding: 25,
      }}
    >
      <div
        style={{
          width: 430,
          background: C.panel,
          borderRadius: 22,
          border: `1px solid ${C.border}`,
          padding: 36,
          boxShadow: "0 25px 60px rgba(0,0,0,0.08)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 28,
          }}
        >
          <div
            style={{
              width: 46,
              height: 46,
              borderRadius: 12,
              background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`,
              display: "grid",
              placeItems: "center",
            }}
          >
            <ShieldCheck color="white" size={22} />
          </div>

          <div>
            <div
              style={{
                fontSize: 21,
                fontWeight: 700,
                color: C.text,
              }}
            >
              ComplianceAI
            </div>

            <div
              style={{
                color: C.goldDark,
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
              }}
            >
              FIRST LOGIN
            </div>
          </div>
        </div>

        <h2
          style={{
            marginBottom: 8,
            color: C.text,
          }}
        >
          Change Your Password
        </h2>

        <p
          style={{
            color: C.textDim,
            fontSize: 14,
            marginBottom: 24,
            lineHeight: 1.6,
          }}
        >
          For security reasons, you must change your temporary password before
          accessing ComplianceAI.
        </p>

        <input
          type="password"
          placeholder="Temporary Password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          style={inputStyle}
        />

        <div style={{ height: 14 }} />

        <input
          type="password"
          placeholder="New Password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          style={inputStyle}
        />

        <div style={{ height: 14 }} />

        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          style={inputStyle}
        />

        <div
          style={{
            marginTop: 18,
            background: "#FFF9F0",
            border: `1px solid ${C.border}`,
            borderRadius: 10,
            padding: 14,
            fontSize: 13,
            lineHeight: 1.8,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 8 }}>
            Password Requirements
          </div>

          <div style={{ color: checks.length ? C.green : C.red }}>
            {checks.length ? "✓" : "✗"} At least 8 characters
          </div>

          <div style={{ color: checks.uppercase ? C.green : C.red }}>
            {checks.uppercase ? "✓" : "✗"} One uppercase letter
          </div>

          <div style={{ color: checks.lowercase ? C.green : C.red }}>
            {checks.lowercase ? "✓" : "✗"} One lowercase letter
          </div>

          <div style={{ color: checks.number ? C.green : C.red }}>
            {checks.number ? "✓" : "✗"} One number
          </div>

          <div style={{ color: checks.special ? C.green : C.red }}>
            {checks.special ? "✓" : "✗"} One special character
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: 18,
              background: "#FDECEC",
              color: C.red,
              borderRadius: 10,
              padding: 12,
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {success && (
          <div
            style={{
              marginTop: 18,
              background: "#EAF7EC",
              color: C.green,
              borderRadius: 10,
              padding: 12,
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            <CheckCircle size={16} />
            {success}
          </div>
        )}

        <button
          onClick={changePassword}
          disabled={loading}
          style={{
            width: "100%",
            marginTop: 26,
            padding: "13px",
            borderRadius: 12,
            border: "none",
            background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`,
            color: "white",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: 15,
          }}
        >
          {loading ? (
            <>
              <Loader2
                size={16}
                style={{
                  animation: "spin 1s linear infinite",
                  marginRight: 8,
                }}
              />
              Updating...
            </>
          ) : (
            "Update Password"
          )}
        </button>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%",
  padding: "12px 14px",
  borderRadius: 10,
  border: `1px solid ${C.border}`,
  background: "#FFFDF9",
  fontSize: 14,
  outline: "none",
};