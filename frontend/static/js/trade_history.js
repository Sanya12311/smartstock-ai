async function loadTrades() {
  const body = document.getElementById("trades-body");
  try {
    const trades = await apiGet("/trades");
    if (trades.length === 0) {
      body.innerHTML = `<tr><td colspan="9" class="table-empty">No completed trades yet.</td></tr>`;
      return;
    }
    body.innerHTML = trades
      .map(
        (t) => `
      <tr>
        <td>${t.id}</td>
        <td>${t.broker_name}</td>
        <td><a href="/app/stocks/${t.symbol}"><strong>${t.symbol}</strong></a></td>
        <td class="${t.side === 'BUY' ? 'positive' : 'negative'}">${t.side}</td>
        <td>${t.quantity}</td>
        <td>${t.order_type}</td>
        <td>${t.price !== null ? formatMoney(t.price) : "—"}</td>
        <td><span class="badge-tag badge-risk-low">${t.status}</span></td>
        <td style="font-size:11px;">${new Date(t.updated_at).toLocaleString("en-IN")}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="9" class="table-empty">Failed to load trades: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function downloadTradesCsv() {
  try {
    const response = await apiFetch("/trades/export/csv");
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `smartstock_trades_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  }
}

loadTrades();
