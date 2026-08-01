import { useState } from "react";
import { ShieldCheck, Mail, Lock, LogIn, KeyRound, ArrowLeft, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { GoogleLogin } from "@react-oauth/google";

const BASE = "/api";

// Matches the ivory / antique-gold brand palette used across the rest of
// the app (see AppFull.jsx `CAP`), kept local here since the login screen
// renders before the authenticated app (and its theme system) mounts.
const C = {
  bg: "#FAF7F2",
  bgGradient: "radial-gradient(1200px 720px at 12% -12%, #F3EEE2 0%, #FAF7F2 58%)",
  panel: "#FFFFFF",
  border: "rgba(22, 18, 14, 0.09)",
  text: "#16120E",
  textDim: "#5C5248",
  textFaint: "#8C8278",
  gold: "#C9A96E",
  goldDark: "#B8923A",
  goldGlow: "rgba(201, 169, 110, 0.16)",
  red: "#B85C38",
  green: "#5A7A6A",
};

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11.5, fontWeight: 700, color: C.textFaint, letterSpacing: "0.06em", marginBottom: 6, textTransform: "uppercase" }}>
        {label}
      </div>
      {children}
    </div>
  );
}

const inputStyle = {
  width: "100%",
  padding: "11px 14px",
  borderRadius: 10,
  border: `1px solid ${C.border}`,
  background: "#FFFDF9",
  color: C.text,
  fontSize: 14,
  outline: "none",
};

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Forgot-password sub-flow — a real call to POST /api/auth/forgot-password,
  // which looks the account up by username or email, issues a fresh
  // temporary password, and emails it via real SMTP when the server has
  // SMTP configured. If SMTP isn't configured, the backend says so
  // honestly and returns the temporary password directly instead of
  // claiming an email was sent.
  const [showForgot, setShowForgot] = useState(false);
  const [forgotIdentifier, setForgotIdentifier] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState("");
  const [forgotResult, setForgotResult] = useState(null);

  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [resetSuccess, setResetSuccess] = useState("");

  const passwordChecks = {
    length: newPassword.length >= 8,
    uppercase: /[A-Z]/.test(newPassword),
    lowercase: /[a-z]/.test(newPassword),
    number: /\d/.test(newPassword),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword),
  };

  const isPasswordValid =
    passwordChecks.length &&
    passwordChecks.uppercase &&
    passwordChecks.lowercase &&
    passwordChecks.number &&
    passwordChecks.special;

  async function login({ user } = {}) {
    setError("");
    try {
      const r = await fetch(`${BASE}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
        username: user || username,
        password,
    }),
      });
      if (!r.ok) throw new Error(`Login failed (HTTP ${r.status})`);
      const data = await r.json();
      if (data.must_change_password) {
          localStorage.setItem("token", data.access_token);

          localStorage.setItem(
              "forcePasswordChange",
              JSON.stringify(data.user)
          );

          onLogin({
              ...data.user,
              mustChangePassword: true,
          });

          return;
      }

// Save JWT
localStorage.setItem("token", data.access_token);

// Get logged-in user's details
const me = await fetch(`${BASE}/auth/me`, {
    headers: {
        Authorization: `Bearer ${data.access_token}`,
    },
});

if (!me.ok) {
    throw new Error("Unable to fetch user profile");
}

const profile = await me.json();

// Save user info
localStorage.setItem("user", JSON.stringify(profile));

// Pass user to App.jsx
onLogin(profile);
    } catch (e) {
      setError(e.message || "Login failed. Is the backend running?");
    }
  }

  async function loginWithGoogle(credential) {
  setError("");

  try {
    const r = await fetch(`${BASE}/auth/google`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        credential,
      }),
    });

    if (!r.ok) {
      throw new Error("Google login failed");
    }

    const data = await r.json();

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);

    const me = await fetch(`${BASE}/auth/me`, {
      headers: {
        Authorization: `Bearer ${data.access_token}`,
      },
    });

    if (!me.ok) {
      throw new Error("Unable to fetch user profile");
    }

    const profile = await me.json();

    localStorage.setItem("user", JSON.stringify(profile));

    onLogin(profile);

  } catch (e) {
    setError(e.message || "Google login failed");
  }
}

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    await login();
    setLoading(false);
  }

  async function handleForgotSubmit(e) {
    e.preventDefault();
    setForgotError("");
    setForgotResult(null);
    setForgotLoading(true);
    try {
      const r = await fetch(`${BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: forgotIdentifier }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `Request failed (HTTP ${r.status})`);
      setForgotResult(data.message);
      setOtpSent(true);
    } catch (e) {
      setForgotError(e.message || "Something went wrong. Is the backend running?");
    } finally {
      setForgotLoading(false);
    }
  }

  async function resetPassword() {
    setError("");
    setResetSuccess("");

    if (!otp.trim()) {
        setError("Please enter the OTP.");
        return;
    }

    if (!newPassword) {
        setError("Please enter a new password.");
        return;
    }

    if (!isPasswordValid) {
          setError(
              "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number and one special character."
          );
          return;
      }

    if (newPassword !== confirmPassword) {
        setError("Passwords do not match.");
        return;
    }

    try {
        setResetLoading(true);

        const r = await fetch(`${BASE}/auth/reset-password`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                identifier: forgotIdentifier,
                otp,
                new_password: newPassword,
            }),
        });

        const data = await r.json();

        if (!r.ok) {
            throw new Error(data.detail || "Password reset failed");
        };

        setResetSuccess(data.message);

        setOtp("");
        setNewPassword("");
        setConfirmPassword("");

        setTimeout(() => {
            setShowForgot(false);
            setOtpSent(false);
            setForgotIdentifier("");
            setResetSuccess("");
        }, 2500);

    } catch (e) {
        setError(e.message);
    } finally {
        setResetLoading(false);
    }
}

  function backToSignIn() {
    setShowForgot(false);

    setForgotIdentifier("");

    setForgotError("");

    setForgotResult(null);

    setOtpSent(false);

    setOtp("");

    setNewPassword("");

    setConfirmPassword("");

    setResetSuccess("");
}

  return (
    <div style={{
      minHeight: "100vh", width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
      background: C.bgGradient, fontFamily: "'Outfit', system-ui, sans-serif", padding: 24,
    }}>
      <div style={{
        width: "100%", maxWidth: 420, background: C.panel, borderRadius: 24,
        border: `1px solid ${C.border}`, boxShadow: "0 24px 60px rgba(22,18,14,0.08)", padding: "36px 34px",
      }}>
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 12, display: "grid", placeItems: "center",
            background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`, boxShadow: `0 0 15px ${C.goldGlow}`,
          }}>
            <ShieldCheck size={22} color="#fff" />
          </div>
          <div>
            <div style={{ fontFamily: "'Instrument Serif', serif", fontWeight: 700, fontSize: 19, color: C.text, lineHeight: 1.1 }}>ComplianceAI</div>
            <div style={{ fontSize: 10.5, color: C.gold, letterSpacing: "0.1em", fontWeight: 700, marginTop: 2 }}>ENTERPRISE GOVERNANCE PLATFORM</div>
          </div>
        </div>

        {!showForgot ? (
          <form onSubmit={handleSubmit}>
            <Field label="Username">
              <div style={{ position: "relative" }}>
                <Mail size={15} color={C.textFaint} style={{ position: "absolute", left: 13, top: 13 }} />
                <input
                  type="text" required value={username} onChange={e => setUsername(e.target.value)}
                  style={{ ...inputStyle, paddingLeft: 36 }} placeholder="Username"
                />
              </div>
            </Field>

            <Field label="Password">
              <div style={{ position: "relative" }}>
                <Lock size={15} color={C.textFaint} style={{ position: "absolute", left: 13, top: 13 }} />
                <input
                  type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  style={{ ...inputStyle, paddingLeft: 36 }} placeholder="••••••••"
                />
              </div>
            </Field>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: -8, marginBottom: 16 }}>
              <button
                type="button"
                onClick={() => setShowForgot(true)}
                style={{ background: "none", border: "none", cursor: "pointer", color: C.gold, fontSize: 12, fontWeight: 700, padding: 0 }}
              >
                Forgot password?
              </button>
            </div>

            {error && (
              <div style={{
                display: "flex", gap: 8, alignItems: "flex-start", background: "rgba(184,92,56,0.08)",
                border: `1px solid ${C.red}30`, color: C.red, borderRadius: 10, padding: "10px 12px", fontSize: 12.5, marginBottom: 16,
              }}>
                <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} /> {error}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              style={{
                width: "100%", padding: "13px 0", borderRadius: 12, border: "none", cursor: loading ? "default" : "pointer",
                background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`, color: "#fff", fontWeight: 700, fontSize: 14.5,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8, opacity: loading ? 0.75 : 1,
              }}
            >
              {loading ? <Loader2 size={16} style={{ animation: "spin 0.8s linear infinite" }} /> : <LogIn size={16} />}
              Sign in
            </button>
            <div
              style={{
                marginTop: 18,
                display: "flex",
                justifyContent: "center",
              }}
            >
              <GoogleLogin
                onSuccess={(credentialResponse) =>
                  loginWithGoogle(credentialResponse.credential)
                }
                onError={() => setError("Google Sign-In failed")}
              />
            </div>
          </form>
        ) : (
          <form onSubmit={handleForgotSubmit}>
            <button
              type="button"
              onClick={backToSignIn}
              style={{
                display: "flex", alignItems: "center", gap: 6, background: "none", border: "none",
                cursor: "pointer", color: C.textFaint, fontSize: 12, fontWeight: 600, padding: 0, marginBottom: 18,
              }}
            >
              <ArrowLeft size={13} /> Back to sign in
            </button>

            <div style={{ fontSize: 13, color: C.textDim, lineHeight: 1.5, marginBottom: 18 }}>
              Enter your username or email. We'll send a One-Time Password (OTP) to your registered email. Enter the OTP and choose a new password to reset your account.
            </div>

            <input
              type="text"
              placeholder="Username or Email"
              value={forgotIdentifier}
              onChange={(e) => setForgotIdentifier(e.target.value)}
          />

          {!otpSent && (
              <button
                type="submit"
                disabled={forgotLoading}
                style={{
                    width: "100%",
                    padding: "13px 0",
                    borderRadius: 12,
                    border: "none",
                    cursor: forgotLoading ? "default" : "pointer",
                    background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`,
                    color: "#fff",
                    fontWeight: 700,
                    fontSize: 14.5,
                    marginTop: 16
                }}
            >
                {forgotLoading ? "Sending..." : "Send OTP"}
            </button>
          )}

          {otpSent && (
              <>
                  <div
                      style={{
                          marginTop: 12,
                          marginBottom: 12,
                          padding: "10px",
                          borderRadius: 8,
                          background: "#E8F5E9",
                          color: "#2E7D32",
                          border: "1px solid #81C784",
                          fontSize: 13,
                          fontWeight: 600,
                      }}
                  >
                      OTP sent successfully.
                      <br />
                      OTP expires in 10 minutes.
                  </div>

                  <input
                      type="text"
                      placeholder="Enter OTP"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                  />

                  <input
                      type="password"
                      placeholder="New Password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                  />

                  <div
                    style={{
                        marginTop: 10,
                        marginBottom: 12,
                        padding: 12,
                        borderRadius: 10,
                        background: "#FFF9F0",
                        border: `1px solid ${C.border}`,
                        fontSize: 12,
                    }}
                >
                    <div
                        style={{
                            fontWeight: 700,
                            color:
                                Object.values(passwordChecks).filter(Boolean).length <= 2
                                    ? "#C62828"
                                    : Object.values(passwordChecks).filter(Boolean).length <= 4
                                    ? "#E65100"
                                    : "#2E7D32",
                            marginBottom: 8,
                        }}
                    >
                        Password Strength: {
                            Object.values(passwordChecks).filter(Boolean).length <= 2
                                ? "Weak"
                                : Object.values(passwordChecks).filter(Boolean).length <= 4
                                ? "Medium"
                                : "Strong"
                        }
                    </div>
                    
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>
                        Password Requirements
                    </div>

                    <div style={{ color: passwordChecks.length ? "#2E7D32" : "#C62828" }}>
                        {passwordChecks.length ? "✓" : "✗"} At least 8 characters
                    </div>

                    <div style={{ color: passwordChecks.uppercase ? "#2E7D32" : "#C62828" }}>
                        {passwordChecks.uppercase ? "✓" : "✗"} One uppercase letter
                    </div>

                    <div style={{ color: passwordChecks.lowercase ? "#2E7D32" : "#C62828" }}>
                        {passwordChecks.lowercase ? "✓" : "✗"} One lowercase letter
                    </div>

                    <div style={{ color: passwordChecks.number ? "#2E7D32" : "#C62828" }}>
                        {passwordChecks.number ? "✓" : "✗"} One number
                    </div>

                    <div style={{ color: passwordChecks.special ? "#2E7D32" : "#C62828" }}>
                        {passwordChecks.special ? "✓" : "✗"} One special character
                    </div>
                </div>

                  <input
                      type="password"
                      placeholder="Confirm Password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                  />

                  {error && (
                      <div
                          style={{
                              marginTop: 12,
                              padding: "10px",
                              borderRadius: 8,
                              background: "#FDECEC",
                              color: "#B3261E",
                              border: "1px solid #F5C2C7",
                              fontSize: 13,
                          }}
                      >
                          {error}
                      </div>
                  )}

                  <button
                      type="button"
                      disabled={resetLoading || !isPasswordValid}
                      onClick={resetPassword}
                      style={{
                        width: "100%",
                        padding: "13px 0",
                        borderRadius: 12,
                        border: "none",
                        background: `linear-gradient(135deg, ${C.gold}, ${C.goldDark})`,
                        color: "#fff",
                        fontWeight: 700,
                        cursor:
                            resetLoading || !isPasswordValid
                                ? "not-allowed"
                                : "pointer",
                        opacity:
                            resetLoading || !isPasswordValid
                                ? 0.6
                                : 1,
                    }}
                  >
                      {resetLoading ? "Resetting..." : "Reset Password"}
                  </button>

                  {resetSuccess && (
                      <div
                          style={{
                              marginTop: 12,
                              padding: "10px",
                              borderRadius: 8,
                              background: "#E8F5E9",
                              color: "#2E7D32",
                              border: "1px solid #81C784",
                              fontSize: 13,
                              fontWeight: 600,
                          }}
                      >
                          {resetSuccess}
                      </div>
                  )}
              </>
          )}
                    </form>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "22px 0" }}>
          <div style={{ flex: 1, height: 1, background: C.border }} />
          <div style={{ flex: 1, height: 1, background: C.border }} />
        </div>
      </div>
    </div>
  );
}
