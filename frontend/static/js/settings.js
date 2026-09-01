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
    renderTwoFaCard(user.totp_enabled);
  } catch (err) {
    card.innerHTML = `<div class="error-message visible">Failed to load account: ${escapeHtml(err.message)}</div>`;
  }
}

function renderTwoFaCard(enabled) {
  const card = document.getElementById("twofa-card");
  if (enabled) {
    card.innerHTML = `
      <div class="value"><span class="badge-tag badge-risk-low">ENABLED</span></div>
      <div class="form-group" style="max-width:280px; margin-top:14px;">
        <label>Confirm Password to Disable</label>
        <input type="password" id="twofa-disable-password">
      </div>
      <button class="btn btn-danger btn-sm" onclick="disable2fa()">Disable 2FA</button>
      <div id="twofa-disable-error" class="error-message" style="margin-top:12px;"></div>`;
    document.getElementById("twofa-setup-flow").style.display = "none";
  } else {
    card.innerHTML = `
      <div class="value"><span class="badge-tag badge-unavailable">DISABLED</span></div>
      <p style="font-size:13px; color:var(--text-muted); margin:10px 0;">
        Add an extra layer of security — after entering your password, you'll also need a code from
        an authenticator app to sign in.
      </p>
      <button class="btn btn-primary btn-sm" onclick="startEnable2fa()">Set Up 2FA</button>`;
  }
}

async function startEnable2fa() {
  try {
    const setup = await apiPost("/auth/2fa/setup");
    document.getElementById("twofa-qr-code").src = `data:image/png;base64,${setup.qr_code_base64}`;
    document.getElementById("twofa-secret").textContent = `Manual entry secret: ${setup.secret}`;
    document.getElementById("twofa-setup-flow").style.display = "block";
  } catch (err) {
    alert(err.message);
  }
}

async function confirmEnable2fa() {
  const errorEl = document.getElementById("twofa-setup-error");
  errorEl.classList.remove("visible");
  const code = document.getElementById("twofa-enable-code").value;

  try {
    await apiPost("/auth/2fa/enable", { code });
    document.getElementById("twofa-setup-flow").style.display = "none";
    loadAccount();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function disable2fa() {
  const errorEl = document.getElementById("twofa-disable-error");
  errorEl.classList.remove("visible");
  const password = document.getElementById("twofa-disable-password").value;

  if (!password) {
    errorEl.textContent = "Enter your password to confirm.";
    errorEl.classList.add("visible");
    return;
  }

  try {
    await apiPost("/auth/2fa/disable", { password });
    loadAccount();
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function changePassword() {
  const errorEl = document.getElementById("password-error");
  const successEl = document.getElementById("password-success");
  errorEl.classList.remove("visible");
  successEl.style.display = "none";

  const current_password = document.getElementById("current-password").value;
  const new_password = document.getElementById("new-password").value;
  const confirm_new_password = document.getElementById("confirm-new-password").value;

  if (!current_password || !new_password) {
    errorEl.textContent = "Both current and new password are required.";
    errorEl.classList.add("visible");
    return;
  }
  if (new_password.length < 8) {
    errorEl.textContent = "New password must be at least 8 characters.";
    errorEl.classList.add("visible");
    return;
  }
  if (new_password !== confirm_new_password) {
    errorEl.textContent = "New password and confirmation do not match.";
    errorEl.classList.add("visible");
    return;
  }

  try {
    await apiPost("/auth/change-password", { current_password, new_password });
    successEl.style.display = "block";
    document.getElementById("current-password").value = "";
    document.getElementById("new-password").value = "";
    document.getElementById("confirm-new-password").value = "";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

async function deleteAccount() {
  const errorEl = document.getElementById("delete-account-error");
  errorEl.classList.remove("visible");

  const password = document.getElementById("delete-account-password").value;
  if (!password) {
    errorEl.textContent = "Enter your password to confirm.";
    errorEl.classList.add("visible");
    return;
  }

  if (!confirm("This permanently deletes your account and all data tied to it. This cannot be undone. Continue?")) {
    return;
  }

  try {
    await apiPost("/auth/delete-account", { password });
    clearToken();
    window.location.href = "/login";
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.add("visible");
  }
}

loadAccount();
