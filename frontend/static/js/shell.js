// Shared across every authenticated page: auth guard, market ticker, bell badge.

requireAuth();

async function loadMarketTicker() {
  const symbols = ["NIFTY", "BANKNIFTY", "SENSEX"];
  const container = document.getElementById("market-ticker");
  try {
    const results = await Promise.all(symbols.map((s) => apiGet(`/stocks/${s}`).catch(() => null)));
    container.innerHTML = results
      .map((r, i) => {
        if (!r || r.last_price === null || r.last_price === undefined) {
          return `<div class="item"><span class="symbol">${symbols[i]}</span> <span class="neutral">unavailable</span></div>`;
        }
        const cls = pnlClass(r.change_percent);
        return `<div class="item"><span class="symbol">${symbols[i]}</span> <span>${r.last_price.toFixed(2)}</span> <span class="${cls}">${formatPercent(r.change_percent)}</span></div>`;
      })
      .join("");
  } catch (err) {
    container.innerHTML = `<span class="neutral">Market data unavailable</span>`;
  }
}

async function loadNotificationBadge() {
  try {
    const notifications = await apiGet("/notifications?unread_only=true");
    const badge = document.getElementById("notification-badge");
    if (notifications.length > 0) {
      badge.textContent = notifications.length;
      badge.classList.add("visible");
    }
  } catch (err) {
    // silent — badge just stays hidden if this fails
  }
}

loadMarketTicker();
loadNotificationBadge();
