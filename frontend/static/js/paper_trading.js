async function loadPaperAccount() {
  const cards = document.querySelectorAll("#paper-summary-cards .card");
  try {
    const summary = await apiGet("/paper/account");

    cards[0].querySelector(".value").textContent = formatMoney(summary.balance);
    cards[0].querySelector(".value").className = "value";

    cards[1].querySelector(".value").textContent = formatMoney(summary.holdings_value);
    cards[1].querySelector(".value").className = "value";

    cards[2].querySelector(".value").textContent = formatMoney(summary.net_worth);
    cards[2].querySelector(".value").className = "value";

    const pnlEl = cards[3].querySelector(".value");
    pnlEl.textContent =
      summary.total_pnl === null ? "—" : `${formatMoney(summary.total_pnl)} (${formatPercent(summary.total_pnl_percent)})`;
    pnlEl.className = "value " + pnlClass(summary.total_pnl);

    renderPaperHoldings(summary.holdings);
  } catch (err) {
    cards.forEach((c) => (c.querySelector(".value").textContent = "Error"));
    console.error(err);
  }
}

function renderPaperHoldings(holdings) {
  const body = document.getElementById("paper-holdings-body");
  if (!holdings || holdings.length === 0) {
    body.innerHTML = `<tr><td colspan="7" class="table-empty">No paper holdings yet.</td></tr>`;
    return;
  }
  body.innerHTML = holdings
    .map(
      (h) => `
    <tr>
      <td><a href="/app/stocks/${h.symbol}"><strong>${h.symbol}</strong></a></td>
      <td>${h.quantity}</td>
      <td>${formatMoney(h.avg_buy_price)}</td>
      <td>${h.current_price !== null ? formatMoney(h.current_price) : `<span class="badge-tag badge-unavailable">unavailable</span>`}</td>
      <td>${formatMoney(h.invested_amount)}</td>
      <td>${h.current_value !== null ? formatMoney(h.current_value) : "—"}</td>
      <td class="${pnlClass(h.pnl)}">${h.pnl !== null ? `${formatMoney(h.pnl)} (${formatPercent(h.pnl_percent)})` : "—"}</td>
    </tr>`
    )
    .join("");
}

async function loadPaperOrders() {
  const body = document.getElementById("paper-orders-body");
  try {
    const orders = await apiGet("/paper/orders");
    if (orders.length === 0) {
      body.innerHTML = `<tr><td colspan="7" class="table-empty">No paper orders yet.</td></tr>`;
      return;
    }
    body.innerHTML = orders
      .map(
        (o) => `
      <tr>
        <td><strong>${o.symbol}</strong></td>
        <td class="${o.side === 'BUY' ? 'positive' : 'negative'}">${o.side}</td>
        <td>${o.quantity}</td>
        <td>${o.price !== null ? formatMoney(o.price) : "—"}</td>
        <td><span class="badge-tag ${o.status === 'COMPLETE' ? 'badge-risk-low' : 'badge-risk-high'}">${o.status}</span></td>
        <td style="font-size:11px; color:var(--text-muted);">${o.rejection_reason ? escapeHtml(o.rejection_reason) : "—"}</td>
        <td style="font-size:11px;">${new Date(o.created_at).toLocaleString("en-IN")}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="7" class="table-empty">Failed to load orders: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function placePaperOrder() {
  const symbol = document.getElementById("paper-symbol").value.trim().toUpperCase();
  const side = document.getElementById("paper-side").value;
  const quantity = parseInt(document.getElementById("paper-quantity").value, 10);
  const errorEl = document.getElementById("paper-order-error");
  const resultEl = document.getElementById("paper-order-result");
  errorEl.classList.remove("visible");
  resultEl.textContent = "";

  if (!symbol || !quantity) {
    errorEl.textContent = "Symbol and quantity are required.";
    errorEl.classList.add("visible");
    return;
  }

  try {
    const path = side === "BUY" ? "/paper/orders/buy" : "/paper/orders/sell";
    const order = await apiPost(path, { symbol, quantity });
    resultEl.innerHTML = `Order ${order.status === "COMPLETE" ? '<span class="positive">COMPLETE</span>' : `<span class="negative">REJECTED</span> — ${escapeHtml(order.rejection_reason)}`}`;
    loadPaperAccount();
    loadPaperOrders();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

loadPaperAccount();
loadPaperOrders();
