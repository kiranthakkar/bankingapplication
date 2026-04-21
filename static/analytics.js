(function () {
  "use strict";

  const PALETTE = ["#276050", "#3a8c72", "#56b896", "#88d4bc", "#b4e8d8", "#c5a87a", "#e8c98a", "#f0ddb0"];
  const ACCENT = "#276050";

  let managerConversationId = null;
  let activeTab = "customers";
  const loadedTabs = { customers: false, active: false, dormant: false, premium: false };
  const charts = {};

  const kpiEl = document.getElementById("kpi-summary");
  const managerMessagesEl = document.getElementById("manager-messages");
  const managerFormEl = document.getElementById("manager-chat-form");
  const managerInputEl = document.getElementById("manager-message-input");

  const panels = {
    customers: document.getElementById("panel-customers"),
    active: document.getElementById("panel-active"),
    dormant: document.getElementById("panel-dormant"),
    premium: document.getElementById("panel-premium"),
    chat: document.getElementById("panel-chat"),
  };

  const tabs = {
    customers: document.getElementById("tab-customers"),
    active: document.getElementById("tab-active"),
    dormant: document.getElementById("tab-dormant"),
    premium: document.getElementById("tab-premium"),
    chat: document.getElementById("tab-chat"),
  };

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatMoney(amount) {
    const sign = amount < 0 ? "-" : "";
    return `${sign}$${Math.abs(amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function renderEmpty(container, message) {
    const div = document.createElement("div");
    div.className = "empty-state";
    div.textContent = message;
    container.innerHTML = "";
    container.appendChild(div);
  }

  function makeChart(id, config) {
    if (charts[id]) {
      charts[id].destroy();
    }
    const canvas = document.getElementById(id);
    if (!canvas) return;
    charts[id] = new Chart(canvas, config);
  }

  function chartDefaults() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#22312b", font: { family: "inherit", size: 12 } } },
        tooltip: { bodyFont: { family: "inherit" }, titleFont: { family: "inherit" } },
      },
      scales: {
        x: { ticks: { color: "#5a7a6a", font: { family: "inherit", size: 11 } }, grid: { color: "rgba(0,0,0,0.05)" } },
        y: { ticks: { color: "#5a7a6a", font: { family: "inherit", size: 11 } }, grid: { color: "rgba(0,0,0,0.05)" } },
      },
    };
  }

  function setActiveTab(name) {
    activeTab = name;
    Object.entries(tabs).forEach(([key, btn]) => {
      btn.classList.toggle("is-active", key === name);
      btn.setAttribute("aria-selected", String(key === name));
    });
    Object.entries(panels).forEach(([key, panel]) => {
      panel.classList.toggle("is-hidden", key !== name);
    });
    if (name !== "chat" && !loadedTabs[name]) {
      loadTabData(name);
    }
  }

  async function apiFetch(path) {
    const response = await fetch(path);
    if (response.status === 401) { window.location.href = "/auth/login"; throw new Error("Authentication required."); }
    if (response.status === 403) { throw new Error("Access restricted to bank managers."); }
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch (_) { throw new Error(text || "Unexpected server response."); }
    if (!response.ok) throw new Error(data.detail || "Request failed.");
    return data;
  }

  async function loadKpis() {
    try {
      const data = await apiFetch("/api/manager/summary");
      kpiEl.innerHTML = `
        <div><span class="label">Customers</span><strong>${escapeHtml(data.total_customers ?? "—")}</strong></div>
        <div><span class="label">Accounts</span><strong>${escapeHtml(data.total_accounts ?? "—")}</strong></div>
        <div><span class="label">Transactions</span><strong>${escapeHtml(data.total_transactions ?? "—")}</strong></div>
        <div><span class="label">Total Deposits</span><strong>${data.total_deposits != null ? escapeHtml(formatMoney(data.total_deposits)) : "—"}</strong></div>
        <div><span class="label">Premium</span><strong>${escapeHtml(data.premium_customers ?? "—")}</strong></div>
      `;

      const regular = (data.total_customers || 0) - (data.premium_customers || 0);
      makeChart("chart-kpi-donut", {
        type: "doughnut",
        data: {
          labels: ["Regular", "Premium"],
          datasets: [{
            data: [regular, data.premium_customers || 0],
            backgroundColor: [PALETTE[2], PALETTE[5]],
            borderWidth: 2,
            borderColor: "#fff",
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "65%",
          plugins: {
            legend: { position: "bottom", labels: { color: "#22312b", font: { family: "inherit", size: 12 }, padding: 16 } },
            tooltip: { bodyFont: { family: "inherit" }, titleFont: { family: "inherit" } },
          },
        },
      });
    } catch (err) {
      renderEmpty(kpiEl, err.message || "Failed to load metrics.");
    }
  }

  function renderCustomerRows(customers) {
    if (!customers || !customers.length) return "<div class=\"empty-state\">No customers found.</div>";
    return customers.map((c) => `
      <div class="stack-item">
        <div class="stack-item-main">
          <span class="stack-item-title">${escapeHtml(c.full_name)}</span>
          <span class="stack-item-sub">${escapeHtml(c.email)}</span>
        </div>
        <div class="stack-item-meta"><span class="badge">${escapeHtml(c.tier)}</span></div>
      </div>`).join("");
  }

  function renderAccountRows(accounts, showTxn) {
    if (!accounts || !accounts.length) return "<div class=\"empty-state\">No accounts found.</div>";
    return accounts.map((a) => `
      <div class="stack-item">
        <div class="stack-item-main">
          <span class="stack-item-title">${escapeHtml(a.account_name)}</span>
          <span class="stack-item-sub">${escapeHtml(a.customer_name)}${a.email ? " · " + escapeHtml(a.email) : ""}</span>
        </div>
        <div class="stack-item-meta">
          <span class="badge">${escapeHtml(a.account_type)}</span>
          ${showTxn && a.txn_count != null ? `<span class="hint">${escapeHtml(a.txn_count)} txns</span>` : ""}
          ${!showTxn && a.last_activity != null ? `<span class="hint">Last: ${escapeHtml(a.last_activity || "never")}</span>` : ""}
          <strong>${escapeHtml(formatMoney(a.balance))}</strong>
        </div>
      </div>`).join("");
  }

  function renderPremiumRows(customers) {
    if (!customers || !customers.length) return "<div class=\"empty-state\">No premium customers found.</div>";
    return customers.map((c) => `
      <div class="stack-item">
        <div class="stack-item-main">
          <span class="stack-item-title">${escapeHtml(c.full_name)}</span>
          <span class="stack-item-sub">${escapeHtml(c.email)}</span>
        </div>
        <div class="stack-item-meta">
          <span class="badge">${escapeHtml(c.tier)}</span>
          <span class="hint">${escapeHtml(c.account_count)} acct${c.account_count !== 1 ? "s" : ""}</span>
          <strong>${escapeHtml(formatMoney(c.total_balance))}</strong>
        </div>
      </div>`).join("");
  }

  async function loadTabData(name) {
    const listEl = document.getElementById("list-" + name);

    try {
      if (name === "customers") {
        renderEmpty(listEl, "Loading…");
        const data = await apiFetch("/api/manager/customers?page_size=50");
        const customers = data.customers || [];

        const tierCounts = {};
        customers.forEach((c) => { tierCounts[c.tier] = (tierCounts[c.tier] || 0) + 1; });
        const tierLabels = Object.keys(tierCounts);
        makeChart("chart-tiers", {
          type: "bar",
          data: {
            labels: tierLabels,
            datasets: [{
              label: "Customers",
              data: tierLabels.map((t) => tierCounts[t]),
              backgroundColor: PALETTE.slice(0, tierLabels.length),
              borderRadius: 6,
            }],
          },
          options: { ...chartDefaults(), plugins: { ...chartDefaults().plugins, legend: { display: false } } },
        });

        listEl.innerHTML = renderCustomerRows(customers);

      } else if (name === "active") {
        renderEmpty(listEl, "Loading…");
        const data = await apiFetch("/api/manager/active-accounts?limit=20&days=30");
        const accounts = data.accounts || [];

        makeChart("chart-active", {
          type: "bar",
          data: {
            labels: accounts.map((a) => a.account_name),
            datasets: [{
              label: "Transactions (30 days)",
              data: accounts.map((a) => a.txn_count),
              backgroundColor: PALETTE[0],
              borderRadius: 6,
            }],
          },
          options: { ...chartDefaults(), indexAxis: "y", plugins: { ...chartDefaults().plugins, legend: { display: false } } },
        });

        listEl.innerHTML = renderAccountRows(accounts, true);

      } else if (name === "dormant") {
        renderEmpty(listEl, "Loading…");
        const data = await apiFetch("/api/manager/dormant-accounts?days_inactive=90&limit=30");
        const accounts = data.accounts || [];

        makeChart("chart-dormant", {
          type: "bar",
          data: {
            labels: accounts.slice(0, 15).map((a) => a.account_name),
            datasets: [{
              label: "Balance",
              data: accounts.slice(0, 15).map((a) => a.balance),
              backgroundColor: PALETTE[5],
              borderRadius: 6,
            }],
          },
          options: { ...chartDefaults(), indexAxis: "y", plugins: { ...chartDefaults().plugins, legend: { display: false } } },
        });

        listEl.innerHTML = renderAccountRows(accounts, false);

      } else if (name === "premium") {
        renderEmpty(listEl, "Loading…");
        const data = await apiFetch("/api/manager/premium-customers");
        const customers = data.customers || [];

        makeChart("chart-premium", {
          type: "bar",
          data: {
            labels: customers.slice(0, 15).map((c) => c.full_name),
            datasets: [{
              label: "Total Deposits",
              data: customers.slice(0, 15).map((c) => c.total_balance),
              backgroundColor: customers.slice(0, 15).map((_, i) => PALETTE[i % PALETTE.length]),
              borderRadius: 6,
            }],
          },
          options: { ...chartDefaults(), plugins: { ...chartDefaults().plugins, legend: { display: false } } },
        });

        listEl.innerHTML = renderPremiumRows(customers);
      }

      loadedTabs[name] = true;
    } catch (err) {
      if (listEl) renderEmpty(listEl, err.message || "Failed to load data.");
    }
  }

  function addManagerMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message message-${role}`;
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    managerMessagesEl.appendChild(div);
    managerMessagesEl.scrollTop = managerMessagesEl.scrollHeight;
  }

  managerFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = managerInputEl.value.trim();
    if (!message) return;

    addManagerMessage("user", message);
    managerInputEl.value = "";
    managerInputEl.disabled = true;
    managerFormEl.querySelector("button[type=submit]").disabled = true;

    try {
      const response = await fetch("/api/manager/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: managerConversationId, message }),
      });
      if (response.status === 401) { window.location.href = "/auth/login"; return; }
      if (response.status === 403) { addManagerMessage("assistant", "Access denied. This chat is restricted to bank managers."); return; }
      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { throw new Error(text || "Unexpected server response."); }
      if (!response.ok) throw new Error(data.detail || "Request failed.");
      managerConversationId = data.conversation_id;
      addManagerMessage("assistant", data.reply);
    } catch (err) {
      addManagerMessage("assistant", `Error: ${err.message}`);
    } finally {
      managerInputEl.disabled = false;
      managerFormEl.querySelector("button[type=submit]").disabled = false;
      managerInputEl.focus();
    }
  });

  tabs.customers.addEventListener("click", () => setActiveTab("customers"));
  tabs.active.addEventListener("click", () => setActiveTab("active"));
  tabs.dormant.addEventListener("click", () => setActiveTab("dormant"));
  tabs.premium.addEventListener("click", () => setActiveTab("premium"));
  tabs.chat.addEventListener("click", () => setActiveTab("chat"));

  loadKpis();
  loadTabData("customers");
})();
