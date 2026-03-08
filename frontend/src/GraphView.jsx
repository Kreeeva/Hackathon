import React, { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";

function buildGraphElements(graph) {
  if (!graph || graph.error) {
    return { nodes: [], edges: [] };
  }

  const nodes = [];
  const edges = [];

  const tx = graph.transaction;
  const txIdStr = String(tx?.id ?? graph.transaction_id ?? "transaction");
  const source = graph.source_account != null ? String(graph.source_account) : null;
  const dest = graph.destination_account != null ? String(graph.destination_account) : null;
  const flagged = Array.isArray(graph.linked_flagged_accounts) ? graph.linked_flagged_accounts : [];
  const devices = Array.isArray(graph.devices) ? graph.devices : [];
  const ips = Array.isArray(graph.ips) ? graph.ips : [];
  const seen = new Set();

  const addNode = (id, label, position, style) => {
    if (seen.has(id)) return;
    seen.add(id);
    nodes.push({ id, data: { label }, position, style });
  };

  const baseStyle = { borderRadius: 12, padding: 8, background: "#0f172a", color: "#e5e7eb", fontSize: 12 };

  addNode(
    "tx-" + txIdStr,
    `Txn ${tx?.tx_id ?? txIdStr}`,
    { x: 0, y: 0 },
    { ...baseStyle, border: "1px solid #38bdf8" }
  );

  if (source) {
    addNode("src-" + source, `Source\n${source}`, { x: -160, y: 80 }, { ...baseStyle, border: "1px solid #22c55e", borderRadius: 999, fontSize: 11, whiteSpace: "pre-line", textAlign: "center" });
    edges.push({ id: "e-tx-src", source: "tx-" + txIdStr, target: "src-" + source, style: { stroke: "#22c55e" } });
  }

  if (dest) {
    addNode("dst-" + dest, `Destination\n${dest}`, { x: 160, y: 80 }, { ...baseStyle, border: "1px solid #f97316", borderRadius: 999, fontSize: 11, whiteSpace: "pre-line", textAlign: "center" });
    edges.push({
      id: "e-src-dst",
      source: source ? "src-" + source : "tx-" + txIdStr,
      target: "dst-" + dest,
      animated: true,
      style: { stroke: "#f97316" },
    });
  }

  flagged.forEach((acc, idx) => {
    const nid = "flag-" + String(acc) + "-" + idx;
    addNode(nid, `Flagged\n${acc}`, { x: -80 + idx * 80, y: 220 }, { ...baseStyle, border: "1px solid #f97373", borderRadius: 999, fontSize: 11, whiteSpace: "pre-line", textAlign: "center", background: "#111827", color: "#fecaca" });
    if (source) edges.push({ id: "e-src-flag-" + idx, source: "src-" + source, target: nid, style: { stroke: "#f87171" } });
  });

  devices.forEach((dev, idx) => {
    const nid = "dev-" + String(dev) + "-" + idx;
    addNode(nid, `Device\n${dev}`, { x: -260, y: 200 + idx * 70 }, { ...baseStyle, border: "1px dashed #64748b", color: "#cbd5f5", background: "#020617", fontSize: 11, whiteSpace: "pre-line", textAlign: "center" });
    if (source) edges.push({ id: "e-src-dev-" + idx, source: "src-" + source, target: nid, style: { stroke: "#64748b" } });
  });

  ips.forEach((ip, idx) => {
    const nid = "ip-" + String(ip) + "-" + idx;
    addNode(nid, `IP\n${ip}`, { x: 260, y: 200 + idx * 70 }, { ...baseStyle, border: "1px dashed #6366f1", color: "#e0e7ff", background: "#020617", fontSize: 11, whiteSpace: "pre-line", textAlign: "center" });
    if (source) edges.push({ id: "e-src-ip-" + idx, source: "src-" + source, target: nid, style: { stroke: "#6366f1" } });
  });

  return { nodes, edges };
}

export default function GraphView({ graph }) {
  const { nodes, edges } = useMemo(() => buildGraphElements(graph), [graph]);

  if (graph?.error) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-rose-300">
        {graph.error}
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-slate-500">
        Run an investigation to see the transaction graph.
      </div>
    );
  }

  return (
    <div className="h-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} color="#1f2937" />
        <MiniMap
          nodeColor={() => "#0f172a"}
          maskColor="rgba(15,23,42,0.7)"
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}

