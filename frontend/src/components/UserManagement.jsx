import { useEffect, useState } from "react";
import {
  Users,
  Plus,
  Trash2,
  Shield,
  RefreshCw,
} from "lucide-react";

const BASE = "/api";

// Same ivory/gold palette as AppFull.jsx's CAP — duplicated locally since
// CAP isn't exported (same pattern Login.jsx already uses for the same
// reason: this component needs to look right without threading a theme
// prop through the whole app).
const C = {
  purple: "#C9A96E",
  purpleDark: "#B8923A",
  purpleGlow: "rgba(201, 169, 110, 0.16)",
  red: "#B85C38",
  redGlow: "rgba(184, 92, 56, 0.12)",
  green: "#5A7A6A",
  greenGlow: "rgba(90, 122, 106, 0.14)",
  panel: "#FFFFFF",
  border: "rgba(22, 18, 14, 0.09)",
  text: "#16120E",
  textDim: "#5C5248",
  textFaint: "#8C8278",
};

function authHeaders(extra = {}) {
  const token = localStorage.getItem("token");
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function api(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });

  if (!res.ok) {
    let msg = "Request failed";
    try {
      const err = await res.json();
      msg = err.detail;
    } catch {}
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  return res.json();
}

const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 10,
  border: `1px solid ${C.border}`,
  background: "#FFFDF9",
  color: C.text,
  fontSize: 13,
  outline: "none",
  fontFamily: "'Outfit', sans-serif",
};

const labelStyle = {
  fontSize: 10.5,
  fontWeight: 700,
  color: C.textFaint,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  marginBottom: 6,
  display: "block",
};

const iconBtnStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 30,
  height: 30,
  borderRadius: 8,
  cursor: "pointer",
  background: "rgba(20, 33, 61, 0.03)",
  border: `1px solid ${C.border}`,
  color: C.textDim,
};

function StatusBadge({ status }) {
  const active = status === "Active" || status === undefined;
  const tone = active ? C.green : C.textFaint;
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", padding: "4px 9px", borderRadius: 6,
      background: `${tone}18`, color: tone, border: `1px solid ${tone}40`,
    }}>
      {status || "Active"}
    </span>
  );
}

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [editingUser, setEditingUser] = useState(null);

const [editForm, setEditForm] = useState({
    role: "",
    department: "",
});

  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    password: "",
    role: "",
    department: "",
});

  const [createUserError, setCreateUserError] = useState("");
  const [createUserSuccess, setCreateUserSuccess] = useState("");

  async function loadUsers() {
    setLoading(true);
    try {
      const [data, depts, me] = await Promise.all([
        api("/users"),
        api("/auth/attribute-options")
        .then((r) => r.departments)
        .catch(() => []),
        api("/users/me"),
      ]);
      setUsers(data);
      setDepartments(depts);
      setCurrentUser(me);
    } catch (e) {
      alert(e.message);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function createUser() {
    setCreateUserError("");
    setCreateUserSuccess("");

    if (!newUser.username.trim()) {
        setCreateUserError("Username is required.");
        return;
    }

    if (!newUser.email.trim()) {
        setCreateUserError("Email is required.");
        return;
    }

    if (!newUser.password.trim()) {
        setCreateUserError("Temporary Password is required.");
        return;
    }

    if (!newUser.role.trim()) {
        setCreateUserError("Role is required.");
        return;
    }

    if (currentUser?.role === "central_admin" && newUser.role !== "central_admin" && !newUser.department.trim()) {
        setCreateUserError("Department is required.");
        return;
    }

    // Optional email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailRegex.test(newUser.email)) {
        setCreateUserError("Please enter a valid email address.");
        return;
    }

    try {
      await api("/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newUser),
      });

      setCreateUserSuccess("User created successfully.");

      setNewUser({
        username: "",
        email: "",
        password: "",
        role: "",
        department: "",
      });

      loadUsers();
    } catch (e) {
  setCreateUserError("");
}
  }

  async function deleteUser(id) {
    if (!window.confirm("Delete this user?")) return;

    try {
      await api(`/users/${id}`, {
        method: "DELETE",
      });

      loadUsers();
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <div className="slide-in" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 11, display: "grid", placeItems: "center",
            background: C.purpleGlow, border: `1px solid ${C.purple}40`, color: C.purple,
          }}>
            <Users size={19} />
          </div>
          <div>
            <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 21, fontWeight: 700, color: C.text }}>
              User Management
            </div>
            <div style={{ fontSize: 11.5, color: C.textFaint, marginTop: 1 }}>Access control across departments and roles</div>
          </div>
        </div>

        <button
          onClick={() => {
            loadUsers();

            setCreateUserError("");
            setCreateUserSuccess("");

            setNewUser({
              username: "",
              email: "",
              password: "",
              role: "",
              department: "",
            });
          }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "9px 16px",
            borderRadius: 10,
            background: "rgba(20, 33, 61, 0.03)",
            color: C.textDim,
            border: `1px solid ${C.border}`,
            fontSize: 12.5,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      <div style={{
        background: C.panel, border: `1px solid ${C.border}`, borderRadius: 20, padding: 22,
        boxShadow: "0 24px 60px -22px rgba(20, 33, 61, 0.10)",
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginBottom: 16 }}>Create User</div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 14 }}>
          <div>
            <label style={labelStyle}>Username</label>
            <input
              style={inputStyle}
              required
              placeholder="Username"
              value={newUser.username}
              onChange={(e) =>
                setNewUser({
                  ...newUser,
                  username: e.target.value,
                })
              }
            />
          </div>

          <div>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              placeholder="Email"
              required
              value={newUser.email}
              onChange={(e) =>
                setNewUser({
                  ...newUser,
                  email: e.target.value,
                })
              }
            />
          </div>

          <div>
            <label style={labelStyle}>Password</label>
            <input
              style={inputStyle}
              type="password"
              required
              placeholder="Password"
              value={newUser.password}
              onChange={(e) =>
                setNewUser({
                  ...newUser,
                  password: e.target.value,
                })
              }
            />

            {createUserError && (
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
                {createUserError}
              </div>
            )}
          </div>

          <div>
            <label style={labelStyle}>Role</label>
            <select
              style={{ ...inputStyle, color: newUser.role ? C.text : C.textFaint }}
              value={newUser.role}
              onChange={(e) => {
                const role = e.target.value;

                setNewUser({
                  ...newUser,
                  role,
                  department: role === "central_admin" ? "Global" : "",
                });
              }}
            >
              <option value="" disabled hidden>Select Role</option>

              {currentUser?.role === "central_admin" && (
                  <option value="central_admin">Central Admin</option>
              )}

              {currentUser?.role === "central_admin" && (
                  <option value="admin">Department Admin</option>
              )}

              <option value="manager">Manager</option>
              <option value="auditor">Auditor</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>

          <div>
            <label style={labelStyle}>Department</label>
            {newUser.role === "central_admin" ? (
              <input
                style={{ ...inputStyle, color: C.textFaint }}
                value="Global"
                disabled
              />
            ) : currentUser?.role === "central_admin" ? (
              <select
                style={{ ...inputStyle, color: newUser.department ? C.text : C.textFaint }}
                value={newUser.department}
                onChange={(e) =>
                  setNewUser({
                    ...newUser,
                    department: e.target.value,
                  })
                }
              >
                <option value="" disabled hidden>Select Department</option>
                {departments.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            ) : (
              <input
                style={{ ...inputStyle, color: C.textFaint }}
                value={newUser.department || currentUser?.department || ""}
                disabled
              />
            )}
          </div>
        </div>

                {createUserSuccess && (
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
            {createUserSuccess}
          </div>
        )}

        <button
          onClick={createUser}
          style={{
            marginTop: 18, display: "flex", alignItems: "center", gap: 7,
            padding: "11px 20px", borderRadius: 10, border: "none", color: "#fff",
            fontWeight: 700, fontSize: 13, cursor: "pointer",
            background: `linear-gradient(135deg, ${C.purple}, ${C.purpleDark})`,
            boxShadow: `0 8px 20px -6px ${C.purple}50`,
          }}
        >
          <Plus size={14} />
          Create User
        </button>
      </div>

      <div style={{
        background: C.panel, border: `1px solid ${C.border}`, borderRadius: 20, padding: 22,
        boxShadow: "0 24px 60px -22px rgba(20, 33, 61, 0.10)", overflowX: "auto",
      }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${C.border}` }}>
              {["ID", "User", "Email", "Department", "Role", "Status", "Actions"].map((h) => (
                <th key={h} style={{
                  textAlign: "left", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.07em",
                  color: C.textFaint, fontWeight: 700, padding: "10px 14px",
                }}>{h}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" style={{ textAlign: "center", padding: 32, color: C.textFaint, fontSize: 13 }}>
                  Loading…
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: "center", padding: 32, color: C.textFaint, fontSize: 13 }}>
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} style={{ borderBottom: `1px solid ${C.border}` }}>
                  <td style={{ padding: "12px 14px", fontSize: 12.5, color: C.textFaint }}>{u.id}</td>

                  <td style={{ padding: "12px 14px", fontSize: 13, fontWeight: 600, color: C.text }}>{u.username}</td>

                  <td style={{ padding: "12px 14px", fontSize: 12.5, color: C.textDim }}>{u.email}</td>

                  <td style={{ padding: "12px 14px", fontSize: 12.5, color: C.textDim }}>{u.department || "-"}</td>

                  <td style={{ padding: "12px 14px" }}>
                  <td style={{ padding: "12px 14px" }}>
                      {u.role === "central_admin"
                        ? "Central Admin"
                        : u.role === "admin"
                        ? "Department Admin"
                        : u.role.charAt(0).toUpperCase() + u.role.slice(1)}
                    </td>
                  </td>

                  <td style={{ padding: "12px 14px" }}>
                    <StatusBadge status={u.status || (u.is_active ? "Active" : "Disabled")} />
                  </td>

                  <td style={{ padding: "12px 14px" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        onClick={() => deleteUser(u.id)}
                        title="Delete user"
                        style={{ ...iconBtnStyle, background: C.redGlow, border: `1px solid ${C.red}30`, color: C.red }}
                      >
                        <Trash2 size={14} />
                      </button>

                      <button
                          style={iconBtnStyle}
                          title="Edit User"
                          onClick={() => {
                              setEditingUser(u);

                              setEditForm({
                                  role: u.role,
                                  department: u.department,
                              });
                          }}
                      >
                          <Shield size={14}/>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {editingUser && (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.45)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: 9999,
              }}
            >
              <div
                style={{
                  background: "#fff",
                  padding: 24,
                  borderRadius: 16,
                  width: 420,
                }}
              >
                <h3>Edit User</h3>

                <div style={{ marginBottom: 12 }}>
                  <label>Username</label>
                  <input
                    style={inputStyle}
                    value={editingUser.username}
                    disabled
                  />
                </div>

                <div style={{ marginBottom: 12 }}>
                  <label>Email</label>
                  <input
                    style={inputStyle}
                    value={editingUser.email}
                    disabled
                  />
                </div>

                <div style={{ marginBottom: 12 }}>
                  <label>Role</label>

                  <select
                    style={inputStyle}
                    value={editForm.role}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        role: e.target.value,
                        department:
                          e.target.value === "central_admin"
                            ? "Global"
                            : editForm.department,
                      })
                    }
                  >
                    <option value="central_admin">Central Admin</option>
                    <option value="admin">Department Admin</option>
                    <option value="manager">Manager</option>
                    <option value="auditor">Auditor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>

                {editForm.role !== "central_admin" ? (
                  <div style={{ marginBottom: 12 }}>
                    <label>Department</label>

                    <select
                      style={inputStyle}
                      value={editForm.department}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          department: e.target.value,
                        })
                      }
                    >
                      {departments.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div style={{ marginBottom: 12 }}>
                    <label>Department</label>

                    <input
                      style={inputStyle}
                      value="Global"
                      disabled
                    />
                  </div>
                )}

                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 10,
                  }}
                >
                  <button onClick={() => setEditingUser(null)}>
                    Cancel
                  </button>

                  <button
                    onClick={async () => {
                      await api(`/users/${editingUser.id}/role`, {
                        method: "PUT",
                        headers: {
                          "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                          role: editForm.role,
                        }),
                      });

                      if (editForm.role !== "central_admin") {
                        await api(`/users/${editingUser.id}/department`, {
                          method: "PUT",
                          headers: {
                            "Content-Type": "application/json",
                          },
                          body: JSON.stringify({
                            department: editForm.department,
                          }),
                        });
                      }

                      setEditingUser(null);
                      loadUsers();
                    }}
                  >
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          )}
      </div>
    </div>
  );
}
