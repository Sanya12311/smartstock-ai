function sentimentBadgeClass(sentiment) {
  if (sentiment === "POSITIVE") return "badge-risk-low";
  if (sentiment === "NEGATIVE") return "badge-risk-high";
  return "badge-risk-medium";
}

function renderNewsSection(symbol, news) {
  const safeSymbol = escapeHtml(symbol);
  if (!news || news.articles.length === 0) {
    return `
      <div class="section-title">${safeSymbol}</div>
      <div class="table-card"><div class="table-empty">No recent news found.</div></div>`;
  }
  return `
    <div class="section-title">${safeSymbol} <span class="badge-tag ${sentimentBadgeClass(news.sentiment_summary.overall)}" style="margin-left:8px;">${news.sentiment_summary.overall}</span></div>
    <div class="table-card">
      ${news.articles
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
        .join("")}
    </div>`;
}

async function loadWatchlistNews() {
  const feed = document.getElementById("news-feed");
  try {
    const watchlist = await apiGet("/watchlist");
    if (watchlist.length === 0) {
      feed.innerHTML = `<div class="loading-text">Your watchlist is empty — add stocks from the Dashboard, or search a symbol above.</div>`;
      return;
    }
    feed.innerHTML = `<div class="loading-text">Loading news for ${watchlist.length} symbol(s)…</div>`;
    const results = await Promise.all(
      watchlist.map((w) => apiGet(`/stocks/${w.symbol}/news`).catch(() => null))
    );
    feed.innerHTML = watchlist.map((w, i) => renderNewsSection(w.symbol, results[i])).join("");
  } catch (err) {
    feed.innerHTML = `<div class="loading-text">Failed to load news: ${escapeHtml(err.message)}</div>`;
  }
}

async function loadSymbolNews() {
  const symbol = document.getElementById("news-search-input").value.trim().toUpperCase();
  if (!symbol) return;
  const feed = document.getElementById("news-feed");
  feed.innerHTML = `<div class="loading-text">Loading news for ${symbol}…</div>`;
  try {
    const news = await apiGet(`/stocks/${symbol}/news`);
    feed.innerHTML = renderNewsSection(symbol, news);
  } catch (err) {
    feed.innerHTML = `<div class="loading-text">Failed to load news for ${symbol}: ${escapeHtml(err.message)}</div>`;
  }
}

loadWatchlistNews();
