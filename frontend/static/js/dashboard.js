function riskBadgeClass(level) {
  if (level === "LOW") return "badge-risk-low";
  if (level === "MEDIUM") return "badge-risk-medium";
  if (level === "HIGH") return "badge-risk-high";
  return "badge-unavailable";
}

async function loadPortfolioSummary() {
  const cards = document.querySelectorAll("#portfolio-summary-cards .card");
  try {
    const summary = await apiGet("/portfolio");

    cards[0].querySelector(".value").textContent = formatMoney(summary.total_invested);
    cards[0].querySelector(".value").className = "value";

    cards[1].querySelector(".value").textContent = formatMoney(summary.total_current_value);
    cards[1].querySelector(".value").className = "value";
    if (summary.prices_partial) {
      const sub = document.createElement("div");
      sub.className = "sub neutral";
      sub.textContent = "Some prices unavailable";
      cards[1].appendChild(sub);
    }

    const pnlEl = cards[2].querySelector(".value");
    pnlEl.textContent = summary.total_pnl === null ? "—" : `${formatMoney(summary.total_pnl)} (${formatPercent(summary.total_pnl_percent)})`;
    pnlEl.className = "value " + pnlClass(summary.total_pnl);

    const riskEl = cards[3].querySelector(".value");
    riskEl.textContent = summary.risk.risk_level;
    riskEl.className = "value";
    const riskBadge = document.createElement("span");
    riskBadge.className = "badge-tag " + riskBadgeClass(summary.risk.risk_level);
    riskBadge.style.marginLeft = "8px";
    riskBadge.style.fontSize = "12px";

    renderHoldings(summary.holdings);
  } catch (err) {
    cards.forEach((c) => (c.querySelector(".value").textContent = "Error"));
    console.error(err);
  }
}

function renderHoldings(holdings) {
  const body = document.getElementById("holdings-body");
  if (!holdings || holdings.length === 0) {
    body.innerHTML = `<tr><td colspan="7" class="table-empty">No holdings yet. Add some via the Portfolio page.</td></tr>`;
    return;
  }

  body.innerHTML = holdings
    .map(
      (h) => `
    <tr>
      <td><strong>${h.symbol}</strong></td>
      <td>${h.quantity}</td>
      <td>${formatMoney(h.buy_price)}</td>
      <td>${h.current_price !== null ? formatMoney(h.current_price) : `<span class="badge-tag badge-unavailable">unavailable</span>`}</td>
      <td>${formatMoney(h.invested_amount)}</td>
      <td>${h.current_value !== null ? formatMoney(h.current_value) : "—"}</td>
      <td class="${pnlClass(h.pnl)}">${h.pnl !== null ? `${formatMoney(h.pnl)} (${formatPercent(h.pnl_percent)})` : "—"}</td>
    </tr>`
    )
    .join("");
}

async function loadWatchlist() {
  const body = document.getElementById("watchlist-body");
  try {
    const items = await apiGet("/watchlist");
    if (items.length === 0) {
      body.innerHTML = `<tr><td colspan="4" class="table-empty">Your watchlist is empty. Add a symbol above.</td></tr>`;
      return;
    }
    body.innerHTML = items
      .map(
        (item) => `
      <tr>
        <td><strong>${item.symbol}</strong><br><span class="neutral" style="font-size:11px;">${item.name}</span></td>
        <td>${item.last_price !== null ? formatMoney(item.last_price) : `<span class="badge-tag badge-unavailable">unavailable</span>`}</td>
        <td class="${pnlClass(item.change_percent)}">${item.change_percent !== null ? formatPercent(item.change_percent) : "—"}</td>
        <td><button class="icon-btn" onclick="removeWatchlistItem('${item.symbol}')" title="Remove">✕</button></td>
      </tr>`
      )
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="4" class="table-empty">Failed to load watchlist.</td></tr>`;
  }
}

async function addWatchlistItem() {
  const input = document.getElementById("watchlist-add-input");
  const symbol = input.value.trim().toUpperCase();
  if (!symbol) return;
  try {
    await apiPost("/watchlist", { symbol });
    input.value = "";
    loadWatchlist();
  } catch (err) {
    alert(err.message);
  }
}

async function removeWatchlistItem(symbol) {
  try {
    await apiDelete(`/watchlist/${symbol}`);
    loadWatchlist();
  } catch (err) {
    alert(err.message);
  }
}

async function askAI() {
  const input = document.getElementById("ai-question-input");
  const responseEl = document.getElementById("ai-response");
  const message = input.value.trim();
  if (!message) return;

  responseEl.textContent = "Thinking…";
  try {
    const result = await apiPost("/chat", { message });
    responseEl.textContent = result.reply + "\n\n" + result.disclaimer;
  } catch (err) {
    responseEl.textContent = "Error: " + err.message;
  }
}

loadPortfolioSummary();
loadWatchlist();
