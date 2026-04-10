(function () {
  const STORAGE_KEY = "banking.bootstrap.v1";
  const TTL_MS = 60 * 1000;

  function readCache() {
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return null;
      }

      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") {
        return null;
      }

      const savedAt = Number(parsed.savedAt || 0);
      if (!savedAt || Date.now() - savedAt > TTL_MS) {
        window.sessionStorage.removeItem(STORAGE_KEY);
        return null;
      }

      return parsed.data || null;
    } catch (_error) {
      return null;
    }
  }

  function writeCache(data) {
    try {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          savedAt: Date.now(),
          data,
        })
      );
    } catch (_error) {
      // Ignore browser storage failures and continue without caching.
    }
  }

  function clearCache() {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch (_error) {
      // Ignore browser storage failures and continue.
    }
  }

  async function loadBootstrapData(options = {}) {
    const forceRefresh = options.forceRefresh === true;
    if (!forceRefresh) {
      const cached = readCache();
      if (cached) {
        return cached;
      }
    }

    const response = await fetch("/api/bootstrap");
    if (response.status === 401) {
      clearCache();
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
      throw new Error(data.detail || "Request failed");
    }

    writeCache(data);
    return data;
  }

  function bindLogoutCacheClear() {
    const logoutLink = document.querySelector(".logout-link");
    if (!logoutLink) {
      return;
    }

    logoutLink.addEventListener("click", () => {
      clearCache();
    });
  }

  bindLogoutCacheClear();

  window.loadBootstrapData = loadBootstrapData;
  window.clearBootstrapCache = clearCache;
})();
