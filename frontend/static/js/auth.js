function showError(message) {
  const el = document.getElementById("error-message");
  el.textContent = message;
  el.classList.add("visible");
}

function hideError() {
  document.getElementById("error-message").classList.remove("visible");
}

let pendingPreAuthToken = null;

async function handleLogin(event) {
  event.preventDefault();
  hideError();

  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    const response = await fetch("/auth/login", { method: "POST", body });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }

    if (data.requires_2fa) {
      pendingPreAuthToken = data.pre_auth_token;
      document.getElementById("login-form").style.display = "none";
      document.getElementById("totp-form").style.display = "block";
      return;
    }

    setToken(data.access_token);
    window.location.href = "/app/dashboard";
  } catch (err) {
    showError(err.message);
  }
}

async function handleTotpVerify(event) {
  event.preventDefault();
  hideError();

  const code = document.getElementById("totp-code").value;

  try {
    const response = await fetch("/auth/2fa/verify-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pre_auth_token: pendingPreAuthToken, code }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Verification failed");
    }

    setToken(data.access_token);
    window.location.href = "/app/dashboard";
  } catch (err) {
    showError(err.message);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  hideError();

  const full_name = document.getElementById("full_name").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  try {
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, password }),
    });
    const data = await response.json();

    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg).join(", ")
        : data.detail;
      throw new Error(detail || "Registration failed");
    }

    window.location.href = "/login?registered=1";
  } catch (err) {
    showError(err.message);
  }
}

// If already logged in, skip straight to the dashboard.
if (getToken() && (window.location.pathname === "/login" || window.location.pathname === "/register" || window.location.pathname === "/")) {
  window.location.href = "/app/dashboard";
}
