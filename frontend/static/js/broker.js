let pendingConnectionToken = null;

async function loadBrokerStatus() {
  const card = document.getElementById("broker-status-card");
  const flow = document.getElementById("connect-flow");
  try {
    const status = await apiGet("/broker/status");

    if (status.status === "CONNECTED") {
      card.innerHTML = `
        <div class="label">Status</div>
        <div class="value"><span class="badge-tag badge-risk-low">CONNECTED</span></div>
        <div class="sub" style="margin-top:8px; color:var(--text-muted);">Broker: ${escapeHtml(status.broker_name)} · Client ID: ${escapeHtml(status.dhan_client_id)} · Connected: ${new Date(status.connected_at).toLocaleString("en-IN")}</div>
        <button class="btn btn-danger btn-sm" style="margin-top:14px;" onclick="disconnectBroker()">Disconnect</button>`;
      flow.style.display = "none";
    } else {
      const badgeClass = status.status === "NOT_CONNECTED" ? "badge-unavailable" : "badge-risk-medium";
      card.innerHTML = `
        <div class="label">Status</div>
        <div class="value"><span class="badge-tag ${badgeClass}">${status.status}</span></div>`;
      flow.style.display = "block";
    }
  } catch (err) {
    card.innerHTML = `<div class="error-message visible">Failed to load status: ${escapeHtml(err.message)}</div>`;
  }
}

async function startBrokerConnection() {
  try {
    const result = await apiPost("/broker/connect/start");
    pendingConnectionToken = result.connection_token;
    document.getElementById("redirect-uri-box").textContent = result.redirect_uri_to_register;
    document.getElementById("login-url-box").style.display = "none";
  } catch (err) {
    alert(err.message);
  }
}

async function submitBrokerCredentials() {
  const errorEl = document.getElementById("credentials-error");
  errorEl.classList.remove("visible");

  if (!pendingConnectionToken) {
    errorEl.textContent = "Click 'Start / Restart Connection' first to get your Redirect URL.";
    errorEl.classList.add("visible");
    return;
  }

  const dhan_client_id = document.getElementById("dhan-client-id").value.trim();
  const app_id = document.getElementById("dhan-app-id").value.trim();
  const app_secret = document.getElementById("dhan-app-secret").value.trim();

  if (!dhan_client_id || !app_id || !app_secret) {
    errorEl.textContent = "All three fields are required.";
    errorEl.classList.add("visible");
    return;
  }

  try {
    const result = await apiPost("/broker/connect/credentials", {
      connection_token: pendingConnectionToken,
      dhan_client_id,
      app_id,
      app_secret,
    });
    const link = document.getElementById("login-url-link");
    link.href = result.login_url;
    document.getElementById("login-url-box").style.display = "block";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function disconnectBroker() {
  if (!confirm("Disconnect your broker account?")) return;
  try {
    await apiDelete("/broker/disconnect");
    loadBrokerStatus();
  } catch (err) {
    alert(err.message);
  }
}

loadBrokerStatus();
