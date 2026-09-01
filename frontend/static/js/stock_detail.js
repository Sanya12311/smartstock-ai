function sentimentBadgeClass(sentiment) {
  if (sentiment === "POSITIVE") return "badge-risk-low";
  if (sentiment === "NEGATIVE") return "badge-risk-high";
  return "badge-risk-medium";
}

function riskBadgeClass(level) {
  if (level === "LOW") return "badge-risk-low";
  if (level === "MEDIUM") return "badge-risk-medium";
  if (level === "HIGH") return "badge-risk-high";
  return "badge-unavailable";
}

async function loadQuote() {
  const header = document.getElementById("quote-header");
  try {
    const quote = await apiGet(`/stocks/${CURRENT_SYMBOL}`);
    header.innerHTML = `
      <h2>${quote.symbol} <span style="font-size:14px; color:var(--text-muted); font-weight:400;">${quote.name}</span></h2>
      <div style="display:flex; gap:24px; align-items:baseline; margin-top:8px;">
        <span style="font-size:28px; font-weight:700;">${quote.last_price !== null ? formatMoney(quote.last_price) : "—"}</span>
        <span class="${pnlClass(quote.change_percent)}">${quote.change !== null ? formatMoney(quote.change) : ""} ${quote.change_percent !== null ? formatPercent(quote.change_percent) : ""}</span>
      </div>
      <div style="display:flex; gap:20px; margin-top:10px; font-size:12px; color:var(--text-muted);">
        <span>Open: ${quote.open !== null ? formatMoney(quote.open) : "—"}</span>
        <span>High: ${quote.high !== null ? formatMoney(quote.high) : "—"}</span>
        <span>Low: ${quote.low !== null ? formatMoney(quote.low) : "—"}</span>
        <span>Prev Close: ${quote.previous_close !== null ? formatMoney(quote.previous_close) : "—"}</span>
        <span>Volume: ${quote.volume !== null ? Number(quote.volume).toLocaleString("en-IN") : "—"}</span>
      </div>`;
  } catch (err) {
    header.innerHTML = `<h2>${CURRENT_SYMBOL}</h2><div class="error-message visible">Quote unavailable: ${escapeHtml(err.message)}</div>`;
  }
}

async function loadAnalysis() {
  const card = document.getElementById("analysis-card");
  const riskDecisionCard = document.getElementById("risk-decision-card");
  try {
    const analysis = await apiGet(`/stocks/${CURRENT_SYMBOL}/analysis`);
    const ind = analysis.indicators;

    card.innerHTML = `
      <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
        <div style="font-size:32px; font-weight:700;">${analysis.technical_score}<span style="font-size:14px; color:var(--text-muted);">/100</span></div>
        <div style="font-size:13px; color:var(--text-muted);">Technical Score</div>
      </div>
      <div style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">
        SMA20: ${ind.sma_20 ?? "—"} · SMA50: ${ind.sma_50 ?? "—"} · RSI14: ${ind.rsi_14 ?? "—"}<br>
        MACD: ${ind.macd ? `${ind.macd.macd_line} / signal ${ind.macd.signal_line}` : "—"}<br>
        Volatility (20d): ${ind.volatility_20d_percent ?? "—"}% · Support: ${ind.support ?? "—"} · Resistance: ${ind.resistance ?? "—"}
      </div>
      <div style="font-size:12px;">
        ${analysis.score_breakdown
          .map(
            (c) => `<div style="margin-bottom:6px;"><strong>${c.component}</strong>: ${c.score}/${c.max} — <span style="color:var(--text-muted);">${c.reason}</span></div>`
          )
          .join("")}
      </div>`;

    const riskBadge = `<span class="badge-tag ${riskBadgeClass(analysis.risk.risk_level)}">${analysis.risk.risk_level} RISK</span>`;
    riskDecisionCard.innerHTML = `
      <div style="margin-bottom:14px;"><strong>Decision: </strong>${analysis.decision.decision} ${riskBadge}</div>
      <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">${analysis.decision.reason}</div>
      <ul style="font-size:12px; color:var(--text-muted); padding-left:18px;">
        ${analysis.risk.reasons.map((r) => `<li>${r}</li>`).join("")}
      </ul>
      <div style="font-size:11px; color:var(--text-muted); margin-top:12px; font-style:italic;">${analysis.decision.disclaimer}</div>`;
  } catch (err) {
    card.innerHTML = `<div class="error-message visible">Technical analysis unavailable: ${escapeHtml(err.message)}</div>`;
    riskDecisionCard.innerHTML = `<div class="loading-text">Unavailable — depends on the same data as Technical Analysis.</div>`;
  }
}

async function loadNews() {
  const card = document.getElementById("news-card");
  try {
    const news = await apiGet(`/stocks/${CURRENT_SYMBOL}/news`);
    if (news.articles.length === 0) {
      card.innerHTML = `<div class="table-empty">No recent news found.</div>`;
      return;
    }
    card.innerHTML = news.articles
      .map(
        (a) => `
      <div style="padding:12px 16px; border-bottom:1px solid var(--border);">
        <a href="${safeUrl(a.url)}" target="_blank" rel="noopener" style="font-size:13px;">${escapeHtml(a.headline)}</a>
        <div style="display:flex; gap:8px; align-items:center; margin-top:6px;">
          <span class="badge-tag ${sentimentBadgeClass(a.sentiment)}">${a.sentiment}</span>
          <span style="font-size:11px; color:var(--text-muted);">${escapeHtml(a.source)}</span>
        </div>
      </div>`
      )
      .join("");
  } catch (err) {
    card.innerHTML = `<div class="table-empty">News unavailable: ${escapeHtml(err.message)}</div>`;
  }
}

async function searchStock() {
  const q = document.getElementById("stock-search-input").value.trim();
  const resultsEl = document.getElementById("search-results");
  if (!q) return;
  try {
    const results = await apiGet(`/stocks/search?q=${encodeURIComponent(q)}`);
    if (results.length === 0) {
      resultsEl.innerHTML = `<div class="loading-text">No matches.</div>`;
      return;
    }
    resultsEl.innerHTML = results
      .map((r) => `<a href="/app/stocks/${encodeURIComponent(r.symbol)}" class="btn btn-secondary btn-sm" style="margin-right:8px; display:inline-block; margin-bottom:6px;">${escapeHtml(r.symbol)} - ${escapeHtml(r.name)}</a>`)
      .join("");
  } catch (err) {
    resultsEl.innerHTML = `<div class="error-message visible">${escapeHtml(err.message)}</div>`;
  }
}

async function addToWatchlist() {
  try {
    await apiPost("/watchlist", { symbol: CURRENT_SYMBOL });
    alert(`${CURRENT_SYMBOL} added to your watchlist.`);
  } catch (err) {
    alert(err.message);
  }
}

function showAlertForm() {
  document.getElementById("alert-form").style.display = "block";
}

document.addEventListener("DOMContentLoaded", () => {
  const typeSelect = document.getElementById("alert-type");
  if (typeSelect) {
    typeSelect.addEventListener("change", () => {
      const needsThreshold = typeSelect.value !== "MACD_CROSS";
      document.getElementById("alert-threshold-group").style.display = needsThreshold ? "block" : "none";
    });
  }
});

async function createAlert() {
  const alert_type = document.getElementById("alert-type").value;
  const thresholdInput = document.getElementById("alert-threshold").value;
  const errorEl = document.getElementById("alert-form-error");
  errorEl.classList.remove("visible");

  const payload = { symbol: CURRENT_SYMBOL, alert_type };
  if (alert_type !== "MACD_CROSS") {
    if (!thresholdInput) {
      errorEl.textContent = "Threshold is required for this alert type.";
      errorEl.classList.add("visible");
      return;
    }
    payload.threshold = parseFloat(thresholdInput);
  }

  try {
    await apiPost("/alerts", payload);
    document.getElementById("alert-form").style.display = "none";
    alert("Alert created.");
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

function toggleLimitPrice() {
  const isLimit = document.getElementById("trade-order-type").value === "LIMIT";
  document.getElementById("limit-price-group").style.display = isLimit ? "block" : "none";
}

async function previewTrade() {
  const side = document.getElementById("trade-side").value;
  const order_type = document.getElementById("trade-order-type").value;
  const quantity = parseInt(document.getElementById("trade-quantity").value, 10);
  const price = order_type === "LIMIT" ? parseFloat(document.getElementById("trade-price").value) : null;
  const previewEl = document.getElementById("trade-preview");
  const errorEl = document.getElementById("trade-error");
  errorEl.classList.remove("visible");
  document.getElementById("trade-result").textContent = "";

  try {
    const preview = await apiPost("/orders/preview", { symbol: CURRENT_SYMBOL, side, quantity, order_type, price });
    previewEl.style.display = "block";
    previewEl.innerHTML = `
      <div><strong>${preview.side} ${preview.quantity} ${preview.symbol}</strong> (${preview.order_type})</div>
      <div style="margin-top:6px;">Current market price: ${preview.current_market_price !== null ? formatMoney(preview.current_market_price) : "unavailable"}</div>
      <div>Estimated value: ${preview.estimated_value !== null ? formatMoney(preview.estimated_value) : "unavailable"}</div>
      <div>Market: ${preview.market_open ? "Open" : "Closed"}</div>
      <div style="margin-top:8px; color:var(--text-muted); font-size:11px;">This is a decision-support estimate, not a guarantee of the final execution price.</div>`;
    document.getElementById("confirm-trade-btn").style.display = "inline-block";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
    previewEl.style.display = "none";
    document.getElementById("confirm-trade-btn").style.display = "none";
  }
}

async function confirmTrade() {
  const mode = document.getElementById("trade-mode").value;
  const side = document.getElementById("trade-side").value;
  const order_type = document.getElementById("trade-order-type").value;
  const quantity = parseInt(document.getElementById("trade-quantity").value, 10);
  const price = order_type === "LIMIT" ? parseFloat(document.getElementById("trade-price").value) : null;
  const errorEl = document.getElementById("trade-error");
  const resultEl = document.getElementById("trade-result");
  errorEl.classList.remove("visible");

  if (!confirm(`Confirm ${mode === "real" ? "REAL" : "PAPER"} ${side} order for ${quantity} ${CURRENT_SYMBOL}?`)) {
    return;
  }

  try {
    let order;
    if (mode === "paper") {
      const path = side === "BUY" ? "/paper/orders/buy" : "/paper/orders/sell";
      order = await apiPost(path, { symbol: CURRENT_SYMBOL, quantity });
    } else {
      const path = side === "BUY" ? "/orders/buy" : "/orders/sell";
      order = await apiPost(path, { symbol: CURRENT_SYMBOL, quantity, order_type, price });
    }
    resultEl.innerHTML = `<span class="positive">Order submitted.</span> Status: <strong>${order.status}</strong>${order.rejection_reason ? ` — ${escapeHtml(order.rejection_reason)}` : ""}`;
    document.getElementById("trade-preview").style.display = "none";
    document.getElementById("confirm-trade-btn").style.display = "none";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function explainStock() {
  const el = document.getElementById("ai-explanation");
  el.textContent = "Thinking…";
  try {
    const result = await apiGet(`/stocks/${CURRENT_SYMBOL}/explain`);
    el.textContent = result.explanation + "\n\n" + result.disclaimer;
  } catch (err) {
    el.textContent = "Error: " + err.message;
  }
}

loadQuote();
loadAnalysis();
loadNews();
