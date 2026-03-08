import React, { useEffect, useState } from "react";
import {
  getHealth,
  investigateTransaction,
  sendFeedback,
} from "./api.js";
import GraphView from "./GraphView.jsx";

function SeverityBadge({ severity }) {
  if (!severity) return null;
  const sev = severity.toLowerCase();
  const label = sev.charAt(0).toUpperCase() + sev.slice(1);
  const cls =
    sev === "high"
      ? "badge-high"
      : sev === "medium"
        ? "badge-medium"
        : "badge-low";
  return <span className={cls}>{label}</span>;
}

function DetectionsList({ evidence }) {
  if (!evidence || !evidence.length) {
    return (
      <div className="text-xs text-slate-500">
        No deterministic fraud patterns were detected.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {evidence.map((item, idx) => (
        <div
          key={idx}
          className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2"
        >
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-semibold text-slate-200">
              {item.type}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 space-y-0.5">
            {Object.entries(item.data || {}).map(([k, v]) => (
              <div key={k}>
                <span className="font-medium text-slate-300">
                  {k}
                </span>
                :{" "}
                <span className="break-all">
                  {Array.isArray(v) ? v.join(", ") : String(v)}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [transactionId, setTransactionId] = useState(
    "transaction:txn_00001",
  );
  const [health, setHealth] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(false);

  const [investigating, setInvestigating] = useState(false);
  const [investigationError, setInvestigationError] = useState("");
  const [result, setResult] = useState(null);

  const [feedbackNote, setFeedbackNote] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  useEffect(() => {
    async function checkHealth() {
      setLoadingHealth(true);
      try {
        const res = await getHealth();
        setHealth(res);
      } catch (e) {
        setHealth({ status: "unavailable" });
      } finally {
        setLoadingHealth(false);
      }
    }
    checkHealth();
  }, []);

  const handleInvestigate = async (e) => {
    e.preventDefault();
    setInvestigating(true);
    setInvestigationError("");
    setFeedbackStatus("");
    try {
      const data = await investigateTransaction(transactionId.trim());
      setResult(data);
    } catch (err) {
      setInvestigationError(err.message || "Investigation failed");
      setResult(null);
    } finally {
      setInvestigating(false);
    }
  };

  const handleFeedback = async (decision) => {
    if (!result?.state?.case_id) return;
    setFeedbackSubmitting(true);
    setFeedbackStatus("");
    try {
      await sendFeedback({
        caseId: result.state.case_id,
        decision,
        note: feedbackNote || undefined,
      });
      setFeedbackStatus(`Feedback submitted: ${decision}`);
    } catch (err) {
      setFeedbackStatus(
        `Failed to submit feedback: ${err.message || err}`,
      );
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const state = result?.state;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-50">
              Agentic Auditor
            </h1>
            <p className="text-xs text-slate-400">
              Explainable fraud detection on SurrealDB with LangGraph.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`inline-flex h-2 w-2 rounded-full ${
                health?.status === "ok"
                  ? "bg-emerald-400"
                  : "bg-amber-400"
              }`}
            />
            <span className="text-slate-400">
              Backend{" "}
              {loadingHealth
                ? "checking..."
                : health?.status === "ok"
                  ? "connected"
                  : "unavailable"}
            </span>
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto max-w-6xl px-4 py-4">
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-5.5rem)]">
          {/* Left panel */}
          <section className="col-span-3 panel">
            <div className="panel-title">Investigation</div>

            <form onSubmit={handleInvestigate} className="space-y-3">
              <label className="block text-xs font-medium text-slate-300">
                Transaction ID
                <input
                  type="text"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500"
                  value={transactionId}
                  onChange={(e) => setTransactionId(e.target.value)}
                  placeholder="transaction:txn_00001"
                />
              </label>

              <button
                type="submit"
                className="primary w-full"
                disabled={investigating || !transactionId.trim()}
              >
                {investigating ? "Running..." : "Run investigation"}
              </button>
            </form>

            {investigationError && (
              <div className="text-xs text-rose-300 mt-2">
                {investigationError}
              </div>
            )}

            <div className="mt-4 space-y-2 text-xs text-slate-400">
              <p className="font-semibold text-slate-200">
                Demo-friendly transactions
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  Star pattern:{" "}
                  <span className="font-mono text-slate-200">
                    transaction:txn_00041
                  </span>{" "}
                  (around account:acct_231)
                </li>
                <li>
                  Circular flow ring:{" "}
                  <span className="font-mono text-slate-200">
                    transaction:txn_00360
                  </span>{" "}
                  (cycle accounts acct_232–acct_236)
                </li>
                <li>
                  Flagged association:{" "}
                  <span className="font-mono text-slate-200">
                    transaction:txn_00390
                  </span>{" "}
                  (accounts linked to confirmed fraud)
                </li>
              </ul>
              <p className="text-[11px]">
                Exact IDs may differ based on seed generation, but any
                transaction involving those accounts should surface the
                patterns.
              </p>
            </div>
          </section>

          {/* Center panel */}
          <section className="col-span-5 panel">
            <div className="flex items-center justify-between mb-1">
              <div className="panel-title">Relationship graph</div>
              {state?.transaction_id && (
                <span className="text-[11px] text-slate-500">
                  Transaction:{" "}
                  <span className="font-mono text-slate-200">
                    {state.transaction_id}
                  </span>
                </span>
              )}
            </div>
            <div className="flex-1 min-h-0">
              <GraphView graph={result?.graph} />
            </div>
          </section>

          {/* Right panel */}
          <section className="col-span-4 panel">
            <div className="flex items-center justify-between mb-1">
              <div className="panel-title">Assessment</div>
              {state?.severity && <SeverityBadge severity={state.severity} />}
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="flex flex-col gap-0.5">
                <span className="text-slate-400">Risk score</span>
                <span className="text-lg font-semibold text-slate-50">
                  {state?.risk_score ?? "—"}
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-slate-400">Alert ID</span>
                <span className="font-mono text-[11px] text-slate-200 break-all">
                  {state?.alert_id || "—"}
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-slate-400">Case ID</span>
                <span className="font-mono text-[11px] text-slate-200 break-all">
                  {state?.case_id || "—"}
                </span>
              </div>
            </div>

            <div className="mt-2 space-y-2">
              <div>
                <div className="text-xs font-semibold text-slate-300 mb-1">
                  Summary
                </div>
                <div className="text-sm text-slate-100">
                  {state?.explanation_short ||
                    "Run an investigation to generate an explanation."}
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-300 mb-1">
                  Analyst-style explanation
                </div>
                <div className="text-xs text-slate-300 leading-relaxed max-h-32 overflow-auto">
                  {state?.explanation_long ||
                    "Once deterministic checks run, a constrained LLM will produce a grounded narrative based only on the evidence below."}
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-300 mb-1">
                  Evidence from deterministic detectors
                </div>
                <DetectionsList evidence={state?.evidence} />
              </div>
            </div>

            <div className="mt-3 border-t border-slate-800 pt-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Analyst feedback
                </span>
                {!state?.case_id && (
                  <span className="text-[11px] text-slate-500">
                    Run an investigation first
                  </span>
                )}
              </div>

              <textarea
                rows={2}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500"
                placeholder="Optional note for this case..."
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
                disabled={!state?.case_id || feedbackSubmitting}
              />

              <div className="flex gap-2">
                <button
                  type="button"
                  className="secondary flex-1"
                  onClick={() =>
                    handleFeedback("confirmed_suspicious")
                  }
                  disabled={!state?.case_id || feedbackSubmitting}
                >
                  Confirm suspicious
                </button>
                <button
                  type="button"
                  className="secondary flex-1"
                  onClick={() => handleFeedback("false_positive")}
                  disabled={!state?.case_id || feedbackSubmitting}
                >
                  False positive
                </button>
                <button
                  type="button"
                  className="secondary flex-1"
                  onClick={() => handleFeedback("escalate")}
                  disabled={!state?.case_id || feedbackSubmitting}
                >
                  Escalate
                </button>
              </div>

              {feedbackStatus && (
                <div className="text-[11px] text-slate-400">
                  {feedbackStatus}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

