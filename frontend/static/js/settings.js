async function loadAccount() {
  const card = document.getElementById("account-card");
  try {
    const user = await apiGet("/auth/me");
    card.innerHTML = `
      <div class="label">Full Name</div>
      <div class="value" style="font-size:16px; margin-bottom:16px;">${user.full_name}</div>
      <div class="label">Email</div>
      <div class="value" style="font-size:16px; margin-bottom:16px;">${user.email}</div>
      <div class="label">Member Since</div>
      <div class="value" style="font-size:16px;">${new Date(user.created_at).toLocaleDateString("en-IN")}</div>`;
  } catch (err) {
    card.innerHTML = `<div class="error-message visible">Failed to load account: ${escapeHtml(err.message)}</div>`;
  }
}

loadAccount();
