let conversationId = null;

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("message-input");
const promptListEl = document.getElementById("prompt-list");
const summaryEl = document.getElementById("customer-summary");
const accountsEl = document.getElementById("accounts-list");
const cardsEl = document.getElementById("cards-list");
const activityEl = document.getElementById("activity-list");
const dataSourceHintEl = document.getElementById("data-source-hint");
const tabAccountsButton = document.getElementById("tab-accounts");
const tabCardsButton = document.getElementById("tab-cards");
const tabActivityButton = document.getElementById("tab-activity");

let activeTab = "accounts";
let canLoadBankingDetails = false;
const loadedTabs = {
  accounts: false,
  cards: false,
  activity: false,
};
const loadingTabs = {
  accounts: false,
  cards: false,
  activity: false,
};

function renderPlaceholder(container, text) {
  container.innerHTML = `<div class="empty-state">${text}</div>`;
}

function formatMoney(amount) {
  const sign = amount < 0 ? "-" : "";
  return `${sign}$${Math.abs(amount).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function renderAccounts(accounts) {
  accountsEl.innerHTML = accounts
    .map(
      (account) => `
        <article class="data-row">
          <div>
            <strong>${account.name}</strong>
            <span class="meta">${account.id} · ${account.kind}</span>
          </div>
          <div class="amount-block">
            <strong>${formatMoney(account.balance)}</strong>
            <span class="meta">${account.currency}</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderCards(cards) {
  cardsEl.innerHTML = cards
    .map(
      (card) => `
        <article class="data-row">
          <div>
            <strong>${card.name}</strong>
            <span class="meta">${card.network} · ${card.id}</span>
          </div>
          <div class="amount-block">
            <strong>•••• ${card.last4}</strong>
            <span class="meta">${card.status}</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderActivity(activity) {
  activityEl.innerHTML = activity
    .map(
      (item) => `
        <article class="data-row">
          <div>
            <strong>${item.description}</strong>
            <span class="meta">${item.account_id} · ${item.posted_on}</span>
          </div>
          <div class="amount-block">
            <strong class="${item.amount < 0 ? "negative" : "positive"}">${formatMoney(item.amount)}</strong>
            <span class="meta">${item.category}</span>
          </div>
        </article>
      `
    )
    .join("");
}

const tabConfig = {
  accounts: {
    button: tabAccountsButton,
    container: accountsEl,
    url: "/api/accounts",
    key: "accounts",
    render: renderAccounts,
    emptyMessage: "No accounts were found for this customer.",
    idleMessage: "Account details will appear here.",
  },
  cards: {
    button: tabCardsButton,
    container: cardsEl,
    url: "/api/cards",
    key: "cards",
    render: renderCards,
    emptyMessage: "No cards were found for this customer.",
    idleMessage: "Card details will appear here.",
  },
  activity: {
    button: tabActivityButton,
    container: activityEl,
    url: "/api/activity",
    key: "recent_activity",
    render: renderActivity,
    emptyMessage: "No recent activity was found for this customer.",
    idleMessage: "Recent activity will appear here.",
  },
};

async function fetchJson(url) {
  const response = await fetch(url);
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Authentication required.");
  }

  const rawText = await response.text();
  let data = {};
  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch (parseError) {
    throw new Error(rawText || "The server returned a non-JSON response.");
  }

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function loadSection(tabName, container, url, key, renderFn, emptyMessage) {
  if (loadedTabs[tabName] || loadingTabs[tabName] || !canLoadBankingDetails) {
    return;
  }

  loadingTabs[tabName] = true;
  renderPlaceholder(container, "Loading...");

  try {
    const data = await fetchJson(url);
    const items = data[key] || [];
    if (!items.length) {
      renderPlaceholder(container, data.message || emptyMessage);
    } else {
      renderFn(items);
    }
    loadedTabs[tabName] = true;
  } catch (error) {
    renderPlaceholder(container, error.message);
  } finally {
    loadingTabs[tabName] = false;
  }
}

async function loadTab(tabName) {
  const activeConfig = tabConfig[tabName];
  await loadSection(
    tabName,
    activeConfig.container,
    activeConfig.url,
    activeConfig.key,
    activeConfig.render,
    activeConfig.emptyMessage
  );
}

function setActiveTab(tabName) {
  activeTab = tabName;

  Object.entries(tabConfig).forEach(([name, config]) => {
    const isActive = name === tabName;
    config.button.classList.toggle("is-active", isActive);
    config.button.setAttribute("aria-selected", isActive ? "true" : "false");
    config.container.classList.toggle("is-hidden", !isActive);
  });
  if (canLoadBankingDetails) {
    void loadTab(tabName);
  }
}

function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const badge = document.createElement("div");
  badge.className = "badge";
  badge.textContent = role === "user" ? "You" : "Agent";

  const body = document.createElement("div");
  body.className = "bubble";
  body.textContent = text;

  wrapper.appendChild(badge);
  wrapper.appendChild(body);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(isLoading) {
  formEl.querySelector("button").disabled = isLoading;
}

async function loadBootstrap() {
  const data = await window.loadBootstrapData();
  const isOracle = data.data_source.startsWith("oracle");

  dataSourceHintEl.textContent = isOracle
    ? "Uses Oracle banking data through SQLcl and agent handoffs."
    : "Uses fallback demo banking data and agent handoffs.";

  if (data.no_matching_account) {
    canLoadBankingDetails = false;
    summaryEl.innerHTML = `
      <div>
        <span class="label">Status</span>
        <strong>No matching account found</strong>
      </div>
      <div>
        <span class="label">User</span>
        <strong>${data.user.email || data.user.preferred_username || data.user.name || "Profile"}</strong>
      </div>
    `;
    renderPlaceholder(accountsEl, data.message || "No matching account found for the logged-in user.");
    renderPlaceholder(cardsEl, data.message || "No matching account found for the logged-in user.");
    renderPlaceholder(activityEl, data.message || "No matching account found for the logged-in user.");
    addMessage("assistant", data.message || "No matching account found for the logged-in user.");
    return;
  }

  canLoadBankingDetails = true;
  const customer = data.customer_summary.customer;
  const snapshot = data.customer_summary.snapshot;
  promptListEl.innerHTML = "";
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
  Object.values(tabConfig).forEach((config) => {
    renderPlaceholder(config.container, config.idleMessage);
  });

  data.suggested_prompts.forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-chip";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      inputEl.value = prompt;
      inputEl.focus();
    });
    promptListEl.appendChild(button);
  });

  addMessage(
    "assistant",
    `Hi, I’m your banking concierge. Your customer snapshot is ready, and the banking tabs will load live account, card, and activity data automatically as you open them. Ask me for balances, transactions, card help, or transfers anytime.`
  );

  await loadTab(activeTab);
}

tabAccountsButton.addEventListener("click", () => setActiveTab("accounts"));
tabCardsButton.addEventListener("click", () => setActiveTab("cards"));
tabActivityButton.addEventListener("click", () => setActiveTab("activity"));

setActiveTab(activeTab);

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) {
    return;
  }

  addMessage("user", message);
  inputEl.value = "";
  setLoading(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
      }),
    });

    const rawText = await response.text();
    let data = null;
    try {
      data = rawText ? JSON.parse(rawText) : {};
    } catch (parseError) {
      throw new Error(rawText || "The server returned a non-JSON error response.");
    }

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      throw new Error(data.detail || "Request failed");
    }

    conversationId = data.conversation_id;
    addMessage("assistant", data.reply);
  } catch (error) {
    addMessage("assistant", `Something went wrong: ${error.message}`);
  } finally {
    setLoading(false);
  }
});

loadBootstrap().catch((error) => {
  summaryEl.innerHTML = `<div class="empty-state">${error.message}</div>`;
  addMessage("assistant", `Something went wrong: ${error.message}`);
});
