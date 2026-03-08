const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Request failed with status ${res.status}: ${text || res.statusText}`,
    );
  }
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return handleResponse(res);
}

export async function investigateTransaction(transactionId) {
  const res = await fetch(`${API_BASE}/investigate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ transaction_id: transactionId }),
  });
  return handleResponse(res);
}

export async function sendFeedback({ caseId, decision, note }) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      case_id: caseId,
      decision,
      note,
    }),
  });
  return handleResponse(res);
}

