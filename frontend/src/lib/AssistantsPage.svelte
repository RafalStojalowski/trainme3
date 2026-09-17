<script>
  import { API_BASE } from "./api.js";

  let { onBack } = $props();

  let assistants = $state([]);
  let usage = $state(null);
  let locations = $state([]);
  let loading = $state(true);
  let selectedId = $state(null);

  let voiceDraft = $state("");
  let traitsDraft = $state("");
  let maxConcurrentDraft = $state(1);

  let togglingStatus = $state(false);
  let savingDetails = $state(false);
  let saveError = $state("");
  let saveOverlayState = $state("idle"); // "idle" | "saving" | "success"
  let saveOverlayTimeout;
  let showLocationPicker = $state(false);
  let togglingLocationId = $state(null);
  let testCallState = $state("idle"); // "idle" | "connecting" | "done"
  let testCallTimeout;

  const statusMeta = {
    active: { label: "Aktywny", className: "status-active" },
    offline: { label: "Offline", className: "status-offline" },
    in_call: { label: "Na rozmowie", className: "status-in-call" },
  };

  let selected = $derived(assistants.find((a) => a.id === selectedId) ?? null);

  let usagePercent = $derived(
    usage && usage.minutes_included > 0
      ? Math.min(100, Math.round((usage.minutes_used / usage.minutes_included) * 100))
      : 0,
  );

  let hasUnsavedChanges = $derived(
    selected
      ? voiceDraft !== selected.voice ||
        traitsDraft !== selected.traits ||
        Number(maxConcurrentDraft) !== selected.max_concurrent_calls
      : false,
  );

  function selectAssistant(id) {
    selectedId = id;
    const assistant = assistants.find((a) => a.id === id);
    if (assistant) {
      voiceDraft = assistant.voice;
      traitsDraft = assistant.traits;
      maxConcurrentDraft = assistant.max_concurrent_calls;
    }
    showLocationPicker = false;
    saveError = "";
    clearTimeout(testCallTimeout);
    testCallState = "idle";
    clearTimeout(saveOverlayTimeout);
    saveOverlayState = "idle";
  }

  async function load() {
    loading = true;
    try {
      const [assistantsRes, usageRes, locationsRes] = await Promise.all([
        fetch(`${API_BASE}/api/assistants`, { credentials: "include" }),
        fetch(`${API_BASE}/api/usage/me`, { credentials: "include" }),
        fetch(`${API_BASE}/api/locations`, { credentials: "include" }),
      ]);

      if (assistantsRes.ok) {
        assistants = await assistantsRes.json();
        if (assistants.length) selectAssistant(assistants[0].id);
      }
      if (usageRes.ok) {
        usage = await usageRes.json();
      }
      if (locationsRes.ok) {
        locations = await locationsRes.json();
      }
    } finally {
      loading = false;
    }
  }

  load();

  function applyAssistantUpdate(updated) {
    assistants = assistants.map((a) => (a.id === updated.id ? updated : a));
  }

  async function patchAssistant(id, payload) {
    const res = await fetch(`${API_BASE}/api/assistants/${id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("PATCH failed");
    const updated = await res.json();
    applyAssistantUpdate(updated);
    return updated;
  }

  async function toggleEnabled() {
    if (!selected || togglingStatus) return;
    togglingStatus = true;
    try {
      const nextStatus = selected.status === "offline" ? "active" : "offline";
      await patchAssistant(selected.id, { status: nextStatus });
    } catch {
      // demo - brak dedykowanej obsługi błędu sieci
    } finally {
      togglingStatus = false;
    }
  }

  async function saveDetails() {
    if (!selected) return;
    savingDetails = true;
    saveError = "";
    clearTimeout(saveOverlayTimeout);
    saveOverlayState = "saving";

    // Overlay ma się utrzymać co najmniej 0.5s, niezależnie od tego, jak szybko odpowie serwer.
    const minDelay = new Promise((resolve) => setTimeout(resolve, 500));
    let success = false;

    try {
      await Promise.all([
        patchAssistant(selected.id, {
          voice: voiceDraft,
          traits: traitsDraft,
          max_concurrent_calls: Number(maxConcurrentDraft),
        }),
        minDelay,
      ]);
      success = true;
    } catch {
      await minDelay;
      saveError = "Nie udało się zapisać zmian. Spróbuj ponownie.";
    } finally {
      savingDetails = false;
    }

    if (success) {
      saveOverlayState = "success";
      saveOverlayTimeout = setTimeout(() => {
        saveOverlayState = "idle";
      }, 600);
    } else {
      saveOverlayState = "idle";
    }
  }

  function isLocationAssigned(locationId) {
    return selected ? selected.locations.some((l) => l.id === locationId) : false;
  }

  async function toggleLocation(locationId) {
    if (!selected) return;
    const current = selected.locations.map((l) => l.id);
    const next = current.includes(locationId)
      ? current.filter((id) => id !== locationId)
      : [...current, locationId];
    togglingLocationId = locationId;
    try {
      await patchAssistant(selected.id, { location_ids: next });
    } catch {
      // demo - brak dedykowanej obsługi błędu sieci
    } finally {
      togglingLocationId = null;
    }
  }

  function startTestCall() {
    if (!selected || testCallState !== "idle") return;
    clearTimeout(testCallTimeout);
    testCallState = "connecting";
    testCallTimeout = setTimeout(() => {
      testCallState = "done";
      testCallTimeout = setTimeout(() => {
        testCallState = "idle";
      }, 2000);
    }, 1500);
  }
</script>

<div class="assistants-page">
  <button class="back-link" onclick={onBack}><i class="fa-solid fa-arrow-left"></i> Wróć do panelu</button>

  <div class="page-header">
    <div class="page-header-text">
      <h1>Zarządzanie <span class="highlight">asystentami</span></h1>
      <p>Monitoruj status wirtualnych konsultantów i sprawdzaj ich konfigurację.</p>
    </div>

    {#if usage}
      <div class="usage-panel">
        <div class="usage-stats">
          <div class="usage-stat">
            <span class="usage-stat-value">{usage.minutes_used}</span>
            <span class="usage-stat-label">wykorzystane minuty</span>
          </div>
          <div class="usage-stat">
            <span class="usage-stat-value">{usage.minutes_included}</span>
            <span class="usage-stat-label">łączna ilość minut</span>
          </div>
        </div>
        <div class="usage-bar">
          <div class="usage-bar-fill" style="width: {usagePercent}%"></div>
        </div>
      </div>
    {/if}
  </div>

  {#if loading}
    <p class="loading-text">Ładowanie...</p>
  {:else}
    <div class="assistants-layout">
      <div class="assistant-tiles">
        {#each assistants as assistant (assistant.id)}
          <button
            class="assistant-tile {statusMeta[assistant.status]?.className ?? ''}"
            class:selected={assistant.id === selectedId}
            onclick={() => selectAssistant(assistant.id)}
          >
            <span class="tile-blob blob-1" aria-hidden="true"></span>
            <span class="tile-blob blob-2" aria-hidden="true"></span>
            <span class="tile-blob blob-3" aria-hidden="true"></span>
            <span class="assistant-avatar"><i class="fa-solid fa-headset"></i></span>
            <span class="assistant-name">{assistant.name}</span>
            <span class="assistant-status">
              <span class="status-dot"></span>
              {statusMeta[assistant.status]?.label ?? assistant.status}
            </span>
          </button>
        {/each}
      </div>

      <div class="assistant-detail">
        {#if saveOverlayState !== "idle"}
          <div class="save-overlay">
            <span class="save-blob save-blob-1" aria-hidden="true"></span>
            <span class="save-blob save-blob-2" aria-hidden="true"></span>
            <span class="save-blob save-blob-3" aria-hidden="true"></span>
            <div class="save-overlay-content">
              {#if saveOverlayState === "saving"}
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <span>Zapisywanie...</span>
              {:else}
                <i class="fa-solid fa-circle-check"></i>
                <span>Zapisano zmiany</span>
              {/if}
            </div>
          </div>
        {/if}

        {#if selected}
          <div class="detail-header">
            <div class="detail-header-text">
              <h2>{selected.name}</h2>
              <span class="assistant-status-badge {statusMeta[selected.status]?.className ?? ''}">
                <span class="status-dot"></span>
                {statusMeta[selected.status]?.label ?? selected.status}
              </span>
            </div>

            <label class="toggle-switch">
              <input
                type="checkbox"
                checked={selected.status !== "offline"}
                disabled={togglingStatus}
                onchange={toggleEnabled}
              />
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
            </label>
          </div>

          <div class="detail-actions">
            <button class="btn-outline" onclick={startTestCall} disabled={testCallState !== "idle"}>
              <i class="fa-solid fa-phone"></i>
              {#if testCallState === "connecting"}
                Łączenie...
              {:else if testCallState === "done"}
                Połączono!
              {:else}
                Rozmowa próbna
              {/if}
            </button>
            <button class="btn-outline" onclick={() => (showLocationPicker = !showLocationPicker)}>
              <i class="fa-solid fa-building"></i> Zarządzaj budynkami
            </button>
          </div>

          {#if showLocationPicker}
            <div class="location-picker">
              {#each locations as location}
                <label class="location-option">
                  <input
                    type="checkbox"
                    checked={isLocationAssigned(location.id)}
                    disabled={togglingLocationId === location.id}
                    onchange={() => toggleLocation(location.id)}
                  />
                  {location.name}
                </label>
              {/each}
              {#if locations.length === 0}
                <p class="detail-placeholder">Brak lokalizacji do przypisania.</p>
              {/if}
            </div>
          {/if}

          <div class="detail-section">
            <h4>Zarządzane budynki</h4>
            <div class="location-chips">
              {#each selected.locations as location}
                <span class="location-chip">{location.name}</span>
              {/each}
              {#if selected.locations.length === 0}
                <span class="detail-placeholder">Brak przypisanych budynków.</span>
              {/if}
            </div>
          </div>

          <div class="detail-stats-row">
            <div class="detail-stat">
              <span class="detail-stat-value">{selected.minutes_used}</span>
              <span class="detail-stat-label">wykorzystane minuty</span>
            </div>
            <div class="detail-field-inline">
              <label for="max-calls">Maks. równoległych rozmów</label>
              <input
                id="max-calls"
                class="field-input-small"
                type="number"
                min="1"
                max="20"
                bind:value={maxConcurrentDraft}
              />
            </div>
          </div>

          <div class="detail-section">
            <label class="detail-label" for="voice-input">Głos</label>
            <input id="voice-input" class="field-input" type="text" bind:value={voiceDraft} />
          </div>

          <div class="detail-section">
            <label class="detail-label" for="traits-input">Cechy szczególne</label>
            <textarea id="traits-input" class="field-textarea" rows="5" bind:value={traitsDraft}></textarea>
          </div>

          {#if saveError}
            <div class="form-error">{saveError}</div>
          {/if}

          <button class="btn-primary" onclick={saveDetails} disabled={!hasUnsavedChanges || savingDetails}>
            {savingDetails ? "Zapisywanie..." : "Zapisz zmiany"}
          </button>
        {:else}
          <p class="detail-placeholder">Wybierz asystenta z listy, aby zobaczyć jego konfigurację.</p>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .assistants-page {
    width: 100%;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    color: #666;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 24px;
    transition: color 0.2s;
  }

  .back-link:hover {
    color: var(--pink);
  }

  .page-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 36px;
  }

  .page-header-text h1 {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .page-header-text p {
    color: #666;
    font-size: 16px;
  }

  .usage-panel {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    flex-shrink: 0;
    width: 420px;
  }

  .usage-bar {
    width: 100%;
    height: 6px;
    background: #f0f0f0;
    border-radius: 999px;
    overflow: hidden;
  }

  .usage-bar-fill {
    height: 100%;
    background: var(--pink);
    border-radius: 999px;
    transition: width 0.4s ease;
  }

  .usage-stats {
    display: flex;
    justify-content: space-between;
    width: 100%;
  }

  .usage-stat {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }

  .usage-stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-dark);
  }

  .usage-stat-label {
    font-size: 12px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }

  .loading-text {
    color: #666;
  }

  .assistants-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(0, 1.3fr);
    gap: 24px;
    align-items: start;
  }

  .assistant-tiles {
    display: grid;
    grid-template-columns: repeat(2, 260px);
    gap: 32px;
  }

  .assistant-tile {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    text-align: center;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 24px;
    aspect-ratio: 1;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.2s ease;
  }

  .assistant-tile:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  }

  .assistant-tile.selected {
    border-color: var(--pink);
    box-shadow: 0 0 0 1px var(--pink);
  }

  .tile-blob {
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(24px);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.4s ease;
  }

  .blob-1 {
    top: -30px;
    left: -30px;
    opacity: 0.35;
  }

  .blob-2 {
    bottom: -34px;
    right: -24px;
  }

  .blob-3 {
    top: 35%;
    right: -38px;
  }

  .assistant-tile:hover .tile-blob {
    opacity: 0.35;
  }

  .assistant-tile:hover .blob-1 {
    animation: float1 3s ease-in-out infinite;
  }

  .assistant-tile:hover .blob-2 {
    animation: float2 3.6s ease-in-out infinite;
  }

  .assistant-tile:hover .blob-3 {
    animation: float3 4.2s ease-in-out infinite;
  }

  @keyframes float1 {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(20px, 20px); }
  }

  @keyframes float2 {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(-18px, -22px); }
  }

  @keyframes float3 {
    0%, 100% { transform: translate(0, 0); }
    50% { transform: translate(-20px, 16px); }
  }

  .assistant-avatar {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 1;
    font-size: 22px;
    color: #333;
  }

  .assistant-name {
    position: relative;
    z-index: 1;
    font-size: 19px;
    font-weight: 600;
  }

  .assistant-status,
  .assistant-status-badge {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 600;
    color: #666;
  }

  .status-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #9ca3af;
  }

  .status-active .status-dot {
    background: #22c55e;
  }

  .status-offline .status-dot {
    background: #9ca3af;
  }

  .status-in-call .status-dot {
    background: var(--pink);
    box-shadow: 0 0 0 0 rgba(255, 82, 162, 0.6);
    animation: pulse 1.6s infinite;
  }

  @keyframes pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(255, 82, 162, 0.5);
    }
    70% {
      box-shadow: 0 0 0 8px rgba(255, 82, 162, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(255, 82, 162, 0);
    }
  }

  .assistant-detail {
    position: relative;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 30px;
    min-height: 340px;
    overflow: hidden;
  }

  .save-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    z-index: 10;
    animation: overlayFadeIn 0.25s ease;
  }

  @keyframes overlayFadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .save-blob {
    position: absolute;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(32px);
    opacity: 0.3;
    pointer-events: none;
  }

  .save-blob-1 {
    top: 5%;
    left: 8%;
    animation: float1 3s ease-in-out infinite;
  }

  .save-blob-2 {
    bottom: 8%;
    right: 12%;
    animation: float2 3.6s ease-in-out infinite;
  }

  .save-blob-3 {
    top: 45%;
    right: -30px;
    animation: float3 4.2s ease-in-out infinite;
  }

  .save-overlay-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    font-size: 15px;
    font-weight: 600;
    color: #333;
  }

  .save-overlay-content i {
    font-size: 30px;
    color: var(--pink);
  }

  .detail-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid #eaeaea;
  }

  .detail-header-text {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .detail-header h2 {
    font-size: 24px;
    font-weight: 700;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    flex-shrink: 0;
  }

  .toggle-switch input {
    position: absolute;
    inset: 0;
    opacity: 0;
    margin: 0;
    cursor: pointer;
    z-index: 1;
  }

  .toggle-track {
    display: block;
    width: 44px;
    height: 24px;
    background: #d1d5db;
    border-radius: 999px;
    position: relative;
    transition: background-color 0.2s ease;
  }

  .toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease;
  }

  .toggle-switch input:checked ~ .toggle-track {
    background: var(--pink);
  }

  .toggle-switch input:checked ~ .toggle-track .toggle-thumb {
    transform: translateX(20px);
  }

  .toggle-switch input:disabled ~ .toggle-track {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .detail-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 24px;
  }

  .btn-outline {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: white;
    border: 1px solid var(--border-gray);
    color: #333;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
  }

  .btn-outline:hover:not(:disabled) {
    border-color: var(--pink);
    color: var(--pink);
  }

  .btn-outline:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .location-picker {
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: #fafafa;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 24px;
  }

  .location-option {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    color: #333;
    cursor: pointer;
  }

  .location-option input {
    width: 16px;
    height: 16px;
    accent-color: var(--pink);
    cursor: pointer;
  }

  .detail-section {
    margin-bottom: 22px;
  }

  .detail-section h4,
  .detail-label {
    display: block;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
    margin-bottom: 8px;
  }

  .location-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .location-chip {
    font-size: 13px;
    font-weight: 600;
    color: #333;
    background: #f7f7f7;
    border: 1px solid #eaeaea;
    padding: 6px 12px;
    border-radius: 999px;
  }

  .detail-placeholder {
    color: #999;
    font-size: 15px;
  }

  .detail-stats-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid #eaeaea;
  }

  .detail-stat {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .detail-stat-value {
    font-size: 22px;
    font-weight: 700;
  }

  .detail-stat-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #999;
  }

  .detail-field-inline {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }

  .detail-field-inline label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #999;
  }

  .field-input-small {
    width: 80px;
    padding: 8px 10px;
    border: 1px solid var(--border-gray);
    border-radius: 6px;
    font-size: 15px;
    font-family: inherit;
    text-align: center;
  }

  .field-input,
  .field-textarea {
    width: 100%;
    padding: 12px 14px;
    border: 1px solid var(--border-gray);
    border-radius: 8px;
    font-size: 14px;
    font-family: inherit;
    color: #333;
  }

  .field-input:focus,
  .field-textarea:focus,
  .field-input-small:focus {
    outline: none;
    border-color: var(--pink);
    box-shadow: 0 0 0 1px var(--pink);
  }

  .field-textarea {
    resize: vertical;
    line-height: 1.5;
  }

  .form-error {
    background: #fff0f5;
    color: #c0175a;
    border: 1px solid #ffd3e6;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    margin-bottom: 16px;
  }

  .btn-primary {
    width: 100%;
    background: black;
    color: white;
    border: none;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .btn-primary:hover:not(:disabled) {
    background: #333;
  }

  .btn-primary:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  @media (max-width: 1100px) {
    .assistants-layout {
      grid-template-columns: 1fr 1fr;
    }

    .assistant-detail {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 640px) {
    .assistants-layout {
      grid-template-columns: 1fr;
    }

    .assistant-tiles {
      grid-template-columns: 1fr;
    }

    .assistant-detail {
      grid-column: auto;
    }

    .page-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }

    .usage-panel {
      width: 100%;
    }

    .usage-stats {
      gap: 24px;
    }
  }
</style>
