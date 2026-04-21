try {
  window.sessionStorage.removeItem("banking.bootstrap.v1");
} catch (_error) {
  // Ignore browser storage failures and continue.
}

const loginButton = document.getElementById("login-button");
loginButton.addEventListener("click", () => {
  loginButton.disabled = true;
  loginButton.textContent = "Redirecting...";
  window.location.href = "/auth/login";
});
