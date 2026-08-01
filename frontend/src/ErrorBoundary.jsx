import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught a render crash:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          fontFamily: "sans-serif",
          padding: "40px",
          maxWidth: "700px",
          margin: "60px auto",
          background: "#fff5f5",
          border: "1px solid #f5c2c7",
          borderRadius: "8px",
          color: "#842029",
        }}>
          <h2 style={{ marginTop: 0 }}>Something went wrong</h2>
          <p>The app hit an error while rendering this page (often caused by
             a failed API call returning no data). Details below:</p>
          <pre style={{
            whiteSpace: "pre-wrap",
            background: "#fff",
            padding: "12px",
            borderRadius: "4px",
            border: "1px solid #eee",
            fontSize: "13px",
          }}>
            {String(this.state.error?.message || this.state.error)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: "16px",
              padding: "8px 16px",
              cursor: "pointer",
              border: "none",
              borderRadius: "4px",
              background: "#842029",
              color: "#fff",
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
