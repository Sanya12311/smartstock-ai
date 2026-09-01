function statusBadgeClass(status) {
  if (status === "TRADED" || status === "PART_TRADED") return "badge-risk-low";
  if (status === "REJECTED" || status === "EXPIRED") return "badge-risk-high";
  if (status === "CANCELLED") return "badge-unavailable";
  return "badge-risk-medium"; // PENDING / TRANSIT
}

async function loadOrders() {
  const body = document.getElementById("orders-body");
  const status = document.getElementById("filter-status").value;
  const symbol = document.getElementById("filter-symbol").value.trim();
  const side = document.getElementById("filter-side").value;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (symbol) params.set("symbol", symbol);
  if (side) params.set("side", side);

  try {
    const orders = await apiGet(`/orders?${params.toString()}`);
    if (orders.length === 0) {
      body.innerHTML = `<tr><td colspan="11" class="table-empty">No orders found.</td></tr>`;
      return;
    }
    body.innerHTML = orders
      .map(
        (o) => `
      <tr>
        <td>${o.id}</td>
        <td>${o.broker_name}</td>
        <td><a href="/app/stocks/${o.symbol}"><strong>${o.symbol}</strong></a></td>
        <td class="${o.side === 'BUY' ? 'positive' : 'negative'}">${o.side}</td>
        <td>${o.quantity}</td>
        <td>${o.order_type}</td>
        <td>${o.price !== null ? formatMoney(o.price) : "—"}</td>
        <td><span class="badge-tag ${statusBadgeClass(o.status)}">${o.status}</span></td>
        <td style="font-size:11px; color:var(--text-muted);">${o.rejection_reason ? escapeHtml(o.rejection_reason) : "—"}</td>
        <td style="font-size:11px;">${new Date(o.created_at).toLocaleString("en-IN")}</td>
        <td>${["PENDING", "TRANSIT"].includes(o.status) ? `<button class="icon-btn" onclick="refreshOrder(${o.id})" title="Refresh status">↻</button> ${o.order_type === "LIMIT" ? `<button class="icon-btn" onclick="modifyOrder(${o.id}, ${o.quantity}, ${o.price})" title="Modify order">✎</button> ` : ""}<button class="icon-btn" onclick="cancelOrder(${o.id})" title="Cancel order">✕</button>` : ""}</td>
      </tr>`
      )
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="11" class="table-empty">Failed to load orders: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function refreshOrder(id) {
  try {
    await apiPost(`/orders/${id}/refresh`);
    loadOrders();
  } catch (err) {
    alert(err.message);
  }
}

async function modifyOrder(id, currentQuantity, currentPrice) {
  const qtyInput = prompt("New quantity:", currentQuantity);
  if (qtyInput === null) return;
  const priceInput = prompt("New price:", currentPrice);
  if (priceInput === null) return;

  const quantity = parseInt(qtyInput, 10);
  const price = parseFloat(priceInput);
  if (!Number.isInteger(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) {
    alert("Quantity and price must be positive numbers.");
    return;
  }

  try {
    await apiPost(`/orders/${id}/modify`, { quantity, price });
    loadOrders();
  } catch (err) {
    alert(err.message);
  }
}

async function cancelOrder(id) {
  if (!confirm("Cancel this order?")) return;
  try {
    await apiPost(`/orders/${id}/cancel`);
    loadOrders();
  } catch (err) {
    alert(err.message);
  }
}

loadOrders();
