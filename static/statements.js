const summaryEl = document.getElementById("customer-summary");
const previewEl = document.getElementById("statements-preview");
const titleEl = document.getElementById("statements-title");
const descriptionEl = document.getElementById("statements-description");
const detailTitleEl = document.getElementById("statement-detail-title");
const detailEl = document.getElementById("statement-detail");
const generateButton = document.getElementById("generate-statements");
const monthlyTabButton = document.getElementById("tab-monthly");
const taxTabButton = document.getElementById("tab-tax");
const communicationsTabButton = document.getElementById("tab-communications");
let activeStatementTab = "monthly";
let bootstrapData = null;
let bootstrapReady = null;
const statementCache = {};

const statementTabs = {
  monthly: {
    button: monthlyTabButton,
    title: "Monthly Statements",
    description: "Browse monthly banking statements for the current customer profile.",
    emptyMessage: "No monthly statements are stored yet. Generate demo statements to create them.",
  },
  tax: {
    button: taxTabButton,
    title: "Tax Statements",
    description: "Tax-related banking documents will be grouped here for year-end access.",
    emptyMessage: "No tax statements are stored yet. Generate demo statements to create them.",
  },
  communications: {
    button: communicationsTabButton,
    title: "Communications",
    description: "Customer notices and secure communications will appear here.",
    emptyMessage: "No communications are stored yet. Generate demo statements to create them.",
  },
};

function renderPlaceholder(container, text) {
  container.innerHTML = `<div class="empty-state">${text}</div>`;
}

function setGenerateButtonVisible(isVisible) {
  const actions = generateButton?.closest(".statement-actions");
  if (!actions) {
    return;
  }
  actions.hidden = !isVisible;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Authentication required.");
  }

  const rawText = await response.text();
  let data = {};
  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch (_error) {
    throw new Error(rawText || "The server returned a non-JSON response.");
  }

  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }

  return data;
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

function renderStatementList(container, items, emptyMessage) {
  if (!items.length) {
    renderPlaceholder(container, emptyMessage);
    return;
  }

  container.innerHTML = items
    .map(
      (item) => `
        <article class="data-row statement-row">
          <div>
            <strong>${escapeHtml(item.title)}</strong>
          </div>
          <button
            class="section-button statement-open-button"
            type="button"
            data-object-name="${escapeHtml(item.object_name)}"
          >
            Preview
          </button>
        </article>
      `
    )
    .join("");
}

async function loadStatements(tabName, forceRefresh = false) {
  if (!bootstrapData) {
    await ensureBootstrap();
  }

  if (bootstrapData?.no_matching_account) {
    renderPlaceholder(previewEl, bootstrapData.message || "No matching account found for the logged-in user.");
    return;
  }

  if (!forceRefresh && statementCache[tabName]) {
    renderStatementList(previewEl, statementCache[tabName], statementTabs[tabName].emptyMessage);
    return;
  }

  renderPlaceholder(previewEl, "Loading statements...");
  const data = await fetchJson(`/api/statements/${tabName}`);
  statementCache[tabName] = data.items || [];
  renderStatementList(previewEl, statementCache[tabName], statementTabs[tabName].emptyMessage);
}

async function primeStatementCache() {
  const tabNames = Object.keys(statementTabs);
  const responses = await Promise.all(
    tabNames.map(async (tabName) => {
      const data = await fetchJson(`/api/statements/${tabName}`);
      return [tabName, data.items || []];
    })
  );

  responses.forEach(([tabName, items]) => {
    statementCache[tabName] = items;
  });

  const hasExistingStatements = responses.some(([, items]) => items.length > 0);
  setGenerateButtonVisible(!hasExistingStatements);
}

async function setActiveStatementTab(tabName, forceRefresh = false) {
  activeStatementTab = tabName;
  Object.entries(statementTabs).forEach(([name, config]) => {
    const isActive = name === tabName;
    config.button.classList.toggle("is-active", isActive);
    config.button.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  const activeTab = statementTabs[tabName];
  titleEl.textContent = activeTab.title;
  descriptionEl.textContent = activeTab.description;
  detailTitleEl.textContent = `${activeTab.title} Preview`;
  detailEl.innerHTML = "Select a statement to preview its contents.";
  await loadStatements(tabName, forceRefresh);
}

async function loadStatementContent(objectName) {
  await ensureBootstrap();
  detailEl.innerHTML = "Loading statement preview...";
  const data = await fetchJson(
    `/api/statements/${activeStatementTab}/content?object_name=${encodeURIComponent(objectName)}`
  );
  detailTitleEl.textContent = data.title || "Statement Preview";
  detailEl.innerHTML = `<pre class="statement-body">${escapeHtml(data.content || "")}</pre>`;
}

async function generateDemoStatements() {
  await ensureBootstrap();
  if (bootstrapData?.no_matching_account) {
    detailEl.innerHTML = bootstrapData.message || "No matching account found for the logged-in user.";
    return;
  }

  generateButton.disabled = true;
  generateButton.textContent = "Generating...";
  detailTitleEl.textContent = "Statement Preview";
  detailEl.innerHTML = "Generating and storing demo statements...";

  try {
    const response = await fetchJson("/api/statements/generate-demo", { method: "POST" });
    Object.keys(statementTabs).forEach((tabName) => {
      delete statementCache[tabName];
    });
    setGenerateButtonVisible(false);
    detailEl.innerHTML = `Generated ${response.uploaded?.length || 0} demo statement objects.`;
    await setActiveStatementTab(activeStatementTab, true);
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "Generate demo statements";
  }
}

async function loadBootstrap() {
  const data = await window.loadBootstrapData();
  bootstrapData = data;
  renderSnapshot(data);
  if (data.no_matching_account) {
    generateButton.disabled = true;
    setGenerateButtonVisible(true);
    renderPlaceholder(previewEl, data.message || "No matching account found for the logged-in user.");
    detailEl.innerHTML = data.message || "No matching account found for the logged-in user.";
  } else {
    generateButton.disabled = false;
  }
  return data;
}

async function ensureBootstrap() {
  if (!bootstrapReady) {
    bootstrapReady = loadBootstrap();
  }
  return bootstrapReady;
}

async function initializeStatementsPage() {
  try {
    const data = await ensureBootstrap();
    if (data.no_matching_account) {
      return;
    }
    await primeStatementCache();
    await setActiveStatementTab("monthly");
  } catch (error) {
    renderPlaceholder(summaryEl, error.message);
    renderPlaceholder(previewEl, error.message);
    detailEl.innerHTML = error.message;
  }
}

Object.entries(statementTabs).forEach(([name, config]) => {
  config.button.addEventListener("click", () => {
    setActiveStatementTab(name).catch((error) => {
      renderPlaceholder(previewEl, error.message);
    });
  });
});

previewEl.addEventListener("click", (event) => {
  const target = event.target.closest(".statement-open-button");
  if (!target) {
    return;
  }
  loadStatementContent(target.dataset.objectName).catch((error) => {
    detailEl.innerHTML = error.message;
  });
});

generateButton.addEventListener("click", () => {
  generateDemoStatements().catch((error) => {
    detailEl.innerHTML = error.message;
  });
});

initializeStatementsPage();
