const summaryEl = document.getElementById("customer-summary");
const detailsEl = document.getElementById("profile-details");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderProfileField(label, value) {
  return `
    <div class="profile-item">
      <span class="label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "Not available")}</strong>
    </div>
  `;
}

function renderSnapshot(data) {
  if (data.no_matching_account || !data.customer_summary) {
    const div = document.createElement("div");
    div.className = "empty-state empty-state-inline";
    div.textContent = data.message || "No matching account found for the logged-in user.";
    summaryEl.innerHTML = "";
    summaryEl.appendChild(div);
    return;
  }

  const customer = data.customer_summary.customer;
  const snapshot = data.customer_summary.snapshot;
  summaryEl.innerHTML = `
    <div>
      <span class="label">Customer</span>
      <strong>${escapeHtml(customer.full_name)}</strong>
    </div>
    <div>
      <span class="label">Tier</span>
      <strong>${escapeHtml(customer.tier)}</strong>
    </div>
    <div>
      <span class="label">Deposits</span>
      <strong>$${escapeHtml(snapshot.total_deposit_balances.toLocaleString())}</strong>
    </div>
    <div>
      <span class="label">Card Balance</span>
      <strong>$${escapeHtml(snapshot.credit_card_balance.toLocaleString())}</strong>
    </div>
  `;
}

async function loadBootstrap() {
  const data = await window.loadBootstrapData();

  renderSnapshot(data);

  if (data.no_matching_account || !data.customer_summary) {
    detailsEl.innerHTML = renderProfileField(
      "Status",
      data.message || "No matching account found for the logged-in user."
    );
    return;
  }

  const customer = data.customer_summary.customer;
  const snapshot = data.customer_summary.snapshot;

  detailsEl.innerHTML = [
    renderProfileField("Customer ID", customer.id),
    renderProfileField("Full Name", customer.full_name),
    renderProfileField("Email", customer.email),
    renderProfileField("Tier", customer.tier),
    renderProfileField("Linked Accounts", String(snapshot.linked_accounts)),
    renderProfileField(
      "Total Deposits",
      `$${snapshot.total_deposit_balances.toLocaleString()}`
    ),
    renderProfileField(
      "Card Balance",
      `$${snapshot.credit_card_balance.toLocaleString()}`
    ),
  ].join("");
}

if (window.applyManagerNav) window.applyManagerNav();
loadBootstrap().catch((error) => {
  const div = document.createElement("div");
  div.className = "empty-state empty-state-inline";
  div.textContent = error.message;
  summaryEl.innerHTML = "";
  summaryEl.appendChild(div);
  detailsEl.innerHTML = renderProfileField("Error", error.message);
});
