// In `npm run dev`, Vite's dev-server proxy forwards the relative "/api"
// path to the backend (see vite.config.js), so no env var is needed.
// In Docker / any static build, there's no dev-server proxy, so we must
// hit the backend directly via VITE_API_BASE (set in docker-compose.yml).
const BASE = import.meta.env.VITE_API_BASE || "/api";

function authHeaders(isJson = false) {
    const token = localStorage.getItem("token");

    const headers = {};

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    if (isJson) {
        headers["Content-Type"] = "application/json";
    }

    return headers;
}

export async function apiFetch(url, options = {}) {
    const token = options.token || localStorage.getItem("token");
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch(url, {
        ...options,
        headers,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function getHealth() {
    const r = await fetch(`${BASE}/health`);
    return r.json();
}

export async function getDashboard() {
    const r = await fetch(`${BASE}/dashboard`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getDashboardMetrics() {
    const r = await fetch(`${BASE}/dashboard/metrics`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getDashboardNarrative() {
    const r = await fetch(`${BASE}/dashboard/narrative`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getDashboardCapabilities() {
    const r = await fetch(`${BASE}/dashboard/capabilities`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getCopilotSuggestions() {
    const r = await fetch(`${BASE}/copilot/suggestions`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getCopilotExamples() {
    const r = await fetch(`${BASE}/copilot/examples`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function askCopilot(prompt) {
    const r = await fetch(`${BASE}/copilot/query`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({ prompt }),
    });

    if (!r.ok) {
        throw new Error(`Copilot query failed (${r.status})`);
    }

    return r.json();
}

export async function getScans() {
    const r = await fetch(`${BASE}/scans`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function getAudit() {
    const r = await fetch(`${BASE}/audit`, {
        headers: authHeaders(),
    });

    return r.json();
}

export async function scanFile(file) {
    const fd = new FormData();
    fd.append("file", file);

    const r = await fetch(`${BASE}/scan`, {
        method: "POST",
        headers: authHeaders(),
        body: fd,
    });

    if (!r.ok) {
        throw new Error(`Scan failed (${r.status})`);
    }

    return r.json();
}

export const SEV = {
    P1: { label: "Critical", color: "var(--p1)" },
    P2: { label: "High", color: "var(--p2)" },
    P3: { label: "Medium", color: "var(--p3)" },
    P4: { label: "Low", color: "var(--p4)" },
};

export const REG_LABEL = {
    gdpr: "GDPR",
    iso27001: "ISO 27001",
    sox: "SOX",
    internal_security: "Internal Security",
    internal_hr: "Internal HR",
};