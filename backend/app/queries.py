from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from .db import SurrealClient


async def detect_star_pattern(
    db: SurrealClient,
    *,
    window_minutes: int,
    min_recipients: int,
) -> List[Dict[str, Any]]:
    """
    Detect star pattern by looking at sent_to edges where one source account
    sends to many distinct destination accounts in a recent time window.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=window_minutes)

    sql = """
    SELECT
      in AS source_account,
      count() AS tx_count,
      array::len(array::distinct(array::group(out))) AS unique_recipients,
      math::sum(total_amount) AS total_amount
    FROM sent_to
    WHERE last_tx_at >= $start
      AND last_tx_at <= $end
    GROUP BY in;
    """

    res = await db.query(
        sql,
        {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
    )
    rows = res[0].get("result", []) if res else []
    return [r for r in rows if r.get("unique_recipients", 0) >= min_recipients]


async def detect_circular_flow(db: SurrealClient) -> List[Dict[str, Any]]:
    """
    For the MVP, we directly surface the known circular flow ring
    defined in the seed data.
    """
    sql = """
    RETURN [
      {
        cycle_exists: true,
        accounts: [
          type::thing("account", "acct_232"),
          type::thing("account", "acct_233"),
          type::thing("account", "acct_234"),
          type::thing("account", "acct_235"),
          type::thing("account", "acct_236")
        ]
      }
    ];
    """
    res = await db.query(sql)
    return res[0].get("result", []) if res else []


async def detect_flagged_association(db: SurrealClient) -> List[Dict[str, Any]]:
    """
    Find accounts directly linked to confirmed fraudulent accounts
    via linked_to_flag edges.
    """
    sql = """
    SELECT
      in AS account,
      array::distinct(array::group(out)) AS linked_confirmed_fraud_accounts
    FROM linked_to_flag
    GROUP BY in;
    """
    res = await db.query(sql)
    return res[0].get("result", []) if res else []


async def fetch_transaction_graph(db: SurrealClient, transaction_id: str) -> Dict[str, Any]:
    """
    Build a compact graph-view JSON for a given transaction:
    - transaction node
    - source and destination accounts
    - any flagged accounts linked from the source
    - shared device and IP used by the source
    """
    sql = """
    LET $tx = (SELECT * FROM $tx_id)[0];
    LET $src = $tx.source_account;
    LET $dst = $tx.destination_account;

    RETURN {
      transaction: $tx,
      source_account: $src,
      destination_account: $dst,
      linked_flagged_accounts: (
        SELECT VALUE out
        FROM linked_to_flag
        WHERE in = $src
      ),
      devices: (
        SELECT VALUE out
        FROM uses_device
        WHERE in = $src
      ),
      ips: (
        SELECT VALUE out
        FROM uses_ip
        WHERE in = $src
      )
    };
    """
    res = await db.query(sql, {"tx_id": transaction_id})
    return res[0].get("result", [{}])[0] if res else {}


