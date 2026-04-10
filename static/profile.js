const summaryEl = document.getElementById("customer-summary");
const detailsEl = document.getElementById("profile-details");

function renderProfileField(label, value) {
  return `
    <div class="profile-item">
      <span class="label">${label}</span>
      <strong>${value || "Not available"}</strong>
    </div>
  `;
}

function renderSnapshot(data) {
  if (data.no_matching_account || !data.customer_summary) {
    summaryEl.innerHTML = `
      <div class="empty-state empty-state-inline">
        ${data.message || "No matching account found for the logged-in user."}
      </div>
    `;
    return;
  }

  const customer = data.customer_summary.customer;
  const snapshot = data.customer_summary.snapshot;
  summaryEl.innerHTML = `
    <div>
      <span class="label">Customer</span>
      <strong>${customer.full_name}</strong>
    </div>
    <div>
      <span class="label">Tier</span>
      <strong>${customer.tier}</strong>
    </div>
    <div>
      <span class="label">Deposits</span>
      <strong>$${snapshot.total_deposit_balances.toLocaleString()}</strong>
    </div>
    <div>
      <span class="label">Card Balance</span>
      <strong>$${snapshot.credit_card_balance.toLocaleString()}</strong>
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

loadBootstrap().catch((error) => {
  summaryEl.innerHTML = `<div class="empty-state empty-state-inline">${error.message}</div>`;
  detailsEl.innerHTML = renderProfileField("Error", error.message);
});
