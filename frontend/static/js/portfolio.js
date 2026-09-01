function riskBadgeClass(level) {
  if (level === "LOW") return "badge-risk-low";
  if (level === "MEDIUM") return "badge-risk-medium";
  if (level === "HIGH") return "badge-risk-high";
  return "badge-unavailable";
}

async function loadPortfolio() {
  const cards = document.querySelectorAll("#portfolio-summary-cards .card");
  try {
    const summary = await apiGet("/portfolio");

    cards[0].querySelector(".value").textContent = formatMoney(summary.total_invested);
    cards[0].querySelector(".value").className = "value";

    cards[1].querySelector(".value").textContent = formatMoney(summary.total_current_value);
    cards[1].querySelector(".value").className = "value";

    const pnlEl = cards[2].querySelector(".value");
    pnlEl.textContent =
      summary.total_pnl === null ? "—" : `${formatMoney(summary.total_pnl)} (${formatPercent(summary.total_pnl_percent)})`;
    pnlEl.className = "value " + pnlClass(summary.total_pnl);

    const riskContent = document.getElementById("risk-content");
    const badge = `<span class="badge-tag ${riskBadgeClass(summary.risk.risk_level)}">${summary.risk.risk_level}</span>`;
    riskContent.innerHTML = `${badge}<ul style="margin-top:10px; padding-left:18px; color:var(--text-muted); font-size:13px;">${summary.risk.reasons
      .map((r) => `<li>${r}</li>`)
      .join("")}</ul>`;

    renderHoldings(summary.holdings);
  } catch (err) {
    cards.forEach((c) => (c.querySelector(".value").textContent = "Error"));
    console.error(err);
  }
}

function renderHoldings(holdings) {
  const body = document.getElementById("holdings-body");
  if (!holdings || holdings.length === 0) {
    body.innerHTML = `<tr><td colspan="9" class="table-empty">No holdings yet. Add one above.</td></tr>`;
    return;
  }

  body.innerHTML = holdings
    .map(
      (h) => `
    <tr>
      <td><a href="/app/stocks/${h.symbol}"><strong>${h.symbol}</strong></a></td>
      <td>${h.quantity}</td>
      <td>${formatMoney(h.buy_price)}</td>
      <td>${h.buy_date}</td>
      <td>${h.current_price !== null ? formatMoney(h.current_price) : `<span class="badge-tag badge-unavailable">unavailable</span>`}</td>
      <td>${formatMoney(h.invested_amount)}</td>
      <td>${h.current_value !== null ? formatMoney(h.current_value) : "—"}</td>
      <td class="${pnlClass(h.pnl)}">${h.pnl !== null ? `${formatMoney(h.pnl)} (${formatPercent(h.pnl_percent)})` : "—"}</td>
      <td><button class="icon-btn" onclick="deleteHolding(${h.id})" title="Delete">✕</button></td>
    </tr>`
    )
    .join("");
}

async function addHolding() {
  const symbol = document.getElementById("add-symbol").value.trim().toUpperCase();
  const quantity = parseInt(document.getElementById("add-quantity").value, 10);
  const buy_price = parseFloat(document.getElementById("add-buy-price").value);
  const buy_date = document.getElementById("add-buy-date").value;
  const errorEl = document.getElementById("add-holding-error");
  errorEl.classList.remove("visible");

  if (!symbol || !quantity || !buy_price || !buy_date) {
    errorEl.textContent = "Please fill in all fields.";
    errorEl.classList.add("visible");
    return;
  }

  try {
    await apiPost("/portfolio/holdings", { symbol, quantity, buy_price, buy_date });
    document.getElementById("add-symbol").value = "";
    document.getElementById("add-quantity").value = "";
    document.getElementById("add-buy-price").value = "";
    document.getElementById("add-buy-date").value = "";
    loadPortfolio();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function deleteHolding(id) {
  if (!confirm("Remove this holding from your portfolio?")) return;
  try {
    await apiDelete(`/portfolio/holdings/${id}`);
    loadPortfolio();
  } catch (err) {
    alert(err.message);
  }
}

loadPortfolio();
