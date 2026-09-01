function alertTypeLabel(type) {
  const labels = {
    PRICE_ABOVE: "Price above",
    PRICE_BELOW: "Price below",
    PROFIT_PERCENT: "Profit % reaches",
    LOSS_PERCENT: "Loss % reaches",
    RSI_OVERBOUGHT: "RSI overbought",
    RSI_OVERSOLD: "RSI oversold",
    MACD_CROSS: "MACD crossover",
  };
  return labels[type] || type;
}

function toggleThresholdField() {
  const needsThreshold = document.getElementById("new-alert-type").value !== "MACD_CROSS";
  document.getElementById("new-alert-threshold-group").style.display = needsThreshold ? "block" : "none";
}

async function loadAlerts() {
  const body = document.getElementById("alerts-body");
  try {
    const alerts = await apiGet("/alerts");
    if (alerts.length === 0) {
      body.innerHTML = `<tr><td colspan="6" class="table-empty">No alerts yet. Create one above.</td></tr>`;
      return;
    }
    body.innerHTML = alerts
      .map(
        (a) => `
      <tr>
        <td><a href="/app/stocks/${a.symbol}"><strong>${a.symbol}</strong></a></td>
        <td>${alertTypeLabel(a.alert_type)}</td>
        <td>${a.threshold !== null ? a.threshold : "—"}</td>
        <td style="font-size:11px;">${a.last_triggered_at ? new Date(a.last_triggered_at).toLocaleString("en-IN") : "Never"}</td>
        <td style="font-size:11px;">${new Date(a.created_at).toLocaleString("en-IN")}</td>
        <td><button class="icon-btn" onclick="deleteAlert(${a.id})" title="Delete">✕</button></td>
      </tr>`
      )
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="table-empty">Failed to load alerts: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function createNewAlert() {
  const symbol = document.getElementById("new-alert-symbol").value.trim().toUpperCase();
  const alert_type = document.getElementById("new-alert-type").value;
  const thresholdInput = document.getElementById("new-alert-threshold").value;
  const errorEl = document.getElementById("new-alert-error");
  errorEl.classList.remove("visible");

  if (!symbol) {
    errorEl.textContent = "Symbol is required.";
    errorEl.classList.add("visible");
    return;
  }

  const payload = { symbol, alert_type };
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
    document.getElementById("new-alert-symbol").value = "";
    document.getElementById("new-alert-threshold").value = "";
    loadAlerts();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function deleteAlert(id) {
  if (!confirm("Delete this alert?")) return;
  try {
    await apiDelete(`/alerts/${id}`);
    loadAlerts();
  } catch (err) {
    alert(err.message);
  }
}

loadAlerts();
