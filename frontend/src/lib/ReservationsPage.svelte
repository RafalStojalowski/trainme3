<script>
  import { fade, fly, slide } from "svelte/transition";
  import { cubicInOut } from "svelte/easing";

  let { onBack } = $props();

  let reservations = $state([]);
  let loading = $state(true);

  function toISODate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  const today = new Date();
  const todayIso = toISODate(today);

  async function load() {
    loading = true;
    try {
      const res = await fetch("/api/reservations", { credentials: "include" });
      if (res.ok) {
        reservations = await res.json();
      }
    } finally {
      loading = false;
    }
  }

  load();

  const weekdayLabels = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"];
  const monthNames = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
  ];
  const monthNamesShort = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze", "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"];

  function formatDate(iso) {
    const [year, month, day] = iso.split("-");
    return `${day}.${month}.${year}`;
  }

  function nightsBetween(startIso, endIso) {
    const diff = new Date(endIso) - new Date(startIso);
    return Math.round(diff / 86400000);
  }

  function reservationWord(n) {
    if (n === 1) return "rezerwacja";
    const lastDigit = n % 10;
    const lastTwo = n % 100;
    if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) return "rezerwacje";
    return "rezerwacji";
  }

  const ASSISTANT_COLORS = ["#FF52A2", "#7C5CFC", "#22B8CF", "#FFA94D", "#51CF66", "#5C7CFA"];

  function assistantColor(id) {
    if (id == null) return "#B5B5B5";
    return ASSISTANT_COLORS[id % ASSISTANT_COLORS.length];
  }

  function initials(name) {
    return name
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  // ---------------------------------------------------------------------
  // Filtry
  // ---------------------------------------------------------------------

  let searchText = $state("");
  let selectedLocations = $state(new Set());
  let rangeStart = $state(null);
  let rangeEnd = $state(null);

  let locationOptions = $derived.by(() => {
    const byId = new Map();
    for (const r of reservations) {
      if (!byId.has(r.location_id)) byId.set(r.location_id, r.location_name);
    }
    return [...byId.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name, "pl"));
  });

  function toggleLocation(id) {
    const next = new Set(selectedLocations);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedLocations = next;
  }

  function selectRangeDay(iso) {
    if (!rangeStart || rangeEnd) {
      rangeStart = iso;
      rangeEnd = null;
      return;
    }
    if (iso === rangeStart) {
      rangeStart = null;
      rangeEnd = null;
      return;
    }
    if (iso < rangeStart) {
      rangeEnd = rangeStart;
      rangeStart = iso;
    } else {
      rangeEnd = iso;
    }
  }

  function clearDateFilter() {
    rangeStart = null;
    rangeEnd = null;
  }

  function clearAllFilters() {
    selectedLocations = new Set();
    clearDateFilter();
    searchText = "";
  }

  let hasActiveFilters = $derived(selectedLocations.size > 0 || !!rangeStart || searchText.trim().length > 0);

  let filteredReservations = $derived.by(() => {
    const q = searchText.trim().toLowerCase();
    return reservations.filter((r) => {
      if (selectedLocations.size > 0 && !selectedLocations.has(r.location_id)) return false;
      if (rangeStart && rangeEnd) {
        if (r.check_out < rangeStart || r.check_in > rangeEnd) return false;
      } else if (rangeStart) {
        if (r.check_in > rangeStart || r.check_out < rangeStart) return false;
      }
      if (q && !r.guest_name.toLowerCase().includes(q)) return false;
      return true;
    });
  });

  function statusOf(r) {
    if (r.check_out < todayIso) return "past";
    if (r.check_in > todayIso) return "upcoming";
    return "active";
  }

  let groups = $derived.by(() => {
    const active = [];
    const upcoming = [];
    const past = [];
    for (const r of filteredReservations) {
      const status = statusOf(r);
      if (status === "active") active.push(r);
      else if (status === "upcoming") upcoming.push(r);
      else past.push(r);
    }
    active.sort((a, b) => (a.check_out < b.check_out ? -1 : 1));
    upcoming.sort((a, b) => (a.check_in < b.check_in ? -1 : 1));
    past.sort((a, b) => (a.check_out > b.check_out ? -1 : 1));
    return [
      { key: "active", label: "W trakcie", icon: "fa-solid fa-door-open", items: active },
      { key: "upcoming", label: "Nadchodzące", icon: "fa-solid fa-arrow-right-long", items: upcoming },
      { key: "past", label: "Zakończone", icon: "fa-solid fa-clock-rotate-left", items: past },
    ];
  });

  let collapsedSections = $state(new Set());

  function toggleSection(key) {
    const next = new Set(collapsedSections);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    collapsedSections = next;
  }

  // ---------------------------------------------------------------------
  // Kalendarz w panelu filtrów (wybór zakresu dat)
  // ---------------------------------------------------------------------

  let filterCursor = $state(new Date(today.getFullYear(), today.getMonth(), 1));

  function buildMonthGrid(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const startWeekday = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) {
      cells.push({ day, iso: toISODate(new Date(year, month, day)) });
    }
    while (cells.length % 7 !== 0) cells.push(null);

    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

    return { weeks, label: `${monthNames[month]} ${year}` };
  }

  let filterMonth = $derived(buildMonthGrid(filterCursor));

  function prevFilterMonth() {
    filterCursor = new Date(filterCursor.getFullYear(), filterCursor.getMonth() - 1, 1);
  }

  function nextFilterMonth() {
    filterCursor = new Date(filterCursor.getFullYear(), filterCursor.getMonth() + 1, 1);
  }

  function isInRange(iso) {
    if (rangeStart && rangeEnd) return iso >= rangeStart && iso <= rangeEnd;
    if (rangeStart) return iso === rangeStart;
    return false;
  }

  // ---------------------------------------------------------------------
  // Mini-kalendarz czasu trwania na karcie rezerwacji
  // ---------------------------------------------------------------------

  function buildMiniMonth(startIso, endIso) {
    const [year, month] = startIso.split("-").map(Number);
    const monthIndex = month - 1;
    const startWeekday = (new Date(year, monthIndex, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
    const monthPrefix = `${year}-${String(month).padStart(2, "0")}`;

    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) {
      const iso = `${monthPrefix}-${String(day).padStart(2, "0")}`;
      cells.push({ iso, inRange: iso >= startIso && iso <= endIso });
    }
    while (cells.length % 7 !== 0) cells.push(null);

    return {
      cells,
      label: `${monthNamesShort[monthIndex]} ${year}`,
      overflowsAfter: endIso > `${monthPrefix}-${String(daysInMonth).padStart(2, "0")}`,
    };
  }

  // ---------------------------------------------------------------------
  // Panel szczegółów (overlay)
  // ---------------------------------------------------------------------

  let focusedId = $state(null);
  let detailCursor = $state(null);

  let focusedReservation = $derived(reservations.find((r) => r.id === focusedId) ?? null);
  let detailMonth = $derived(detailCursor ? buildMonthGrid(detailCursor) : null);

  function openDetail(reservation) {
    focusedId = reservation.id;
    const [year, month] = reservation.check_in.split("-").map(Number);
    detailCursor = new Date(year, month - 1, 1);
  }

  function closeDetail() {
    focusedId = null;
  }

  function detailPrevMonth() {
    detailCursor = new Date(detailCursor.getFullYear(), detailCursor.getMonth() - 1, 1);
  }

  function detailNextMonth() {
    detailCursor = new Date(detailCursor.getFullYear(), detailCursor.getMonth() + 1, 1);
  }

  $effect(() => {
    if (focusedId === null) return;
    function onKeydown(event) {
      if (event.key === "Escape") closeDetail();
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  });
</script>

<div class="reservations-page">
  <button class="back-link" onclick={onBack}><i class="fa-solid fa-arrow-left"></i> Wróć do panelu</button>

  <div class="page-header">
    <h1>Wszystkie <span class="highlight">rezerwacje</span></h1>
    <p>Filtruj po lokalizacji i dacie, sprawdzaj długość pobytu i który asystent obsłużył rezerwację.</p>
  </div>

  {#if loading}
    <p class="loading-text">Ładowanie...</p>
  {:else}
    <div class="reservations-layout" class:has-focus={focusedId !== null}>
      <aside class="filters-panel">
        <div class="filter-block">
          <label class="filter-label" for="guest-search">Szukaj gościa</label>
          <div class="search-input">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input id="guest-search" type="text" placeholder="Imię i nazwisko..." bind:value={searchText} />
          </div>
        </div>

        <div class="filter-block">
          <span class="filter-label">Lokalizacja</span>
          {#if locationOptions.length === 0}
            <p class="filter-empty">Brak lokalizacji z rezerwacjami.</p>
          {:else}
            <div class="chip-row">
              {#each locationOptions as loc (loc.id)}
                <button
                  type="button"
                  class="chip"
                  class:active={selectedLocations.has(loc.id)}
                  onclick={() => toggleLocation(loc.id)}
                >
                  <i class="fa-solid fa-location-dot"></i>
                  {loc.name}
                </button>
              {/each}
            </div>
          {/if}
        </div>

        <div class="filter-block">
          <div class="filter-label-row">
            <span class="filter-label">Zakres dat</span>
            {#if rangeStart}
              <button type="button" class="clear-link" onclick={clearDateFilter}>Wyczyść</button>
            {/if}
          </div>

          <div class="filter-calendar">
            <div class="filter-calendar-nav">
              <button type="button" class="nav-btn-sm" onclick={prevFilterMonth} aria-label="Poprzedni miesiąc">
                <i class="fa-solid fa-chevron-left"></i>
              </button>
              <span class="filter-calendar-label">{filterMonth.label}</span>
              <button type="button" class="nav-btn-sm" onclick={nextFilterMonth} aria-label="Następny miesiąc">
                <i class="fa-solid fa-chevron-right"></i>
              </button>
            </div>
            <div class="mini-weekdays">
              {#each weekdayLabels as label}<span>{label}</span>{/each}
            </div>
            {#key filterCursor.getTime()}
              <div class="filter-calendar-weeks" in:fade={{ duration: 180 }}>
                {#each filterMonth.weeks as week}
                  <div class="filter-calendar-row">
                    {#each week as cell}
                      {#if cell}
                        <button
                          type="button"
                          class="filter-day"
                          class:in-range={isInRange(cell.iso)}
                          class:range-edge={cell.iso === rangeStart || cell.iso === rangeEnd}
                          class:today={cell.iso === todayIso}
                          onclick={() => selectRangeDay(cell.iso)}
                        >
                          {cell.day}
                        </button>
                      {:else}
                        <span class="filter-day empty"></span>
                      {/if}
                    {/each}
                  </div>
                {/each}
              </div>
            {/key}
          </div>

          {#if rangeStart}
            <p class="filter-hint" transition:slide={{ duration: 200 }}>
              {#if rangeEnd}
                {formatDate(rangeStart)} – {formatDate(rangeEnd)}
              {:else}
                Wybierz drugi dzień (od {formatDate(rangeStart)})
              {/if}
            </p>
          {/if}
        </div>

        {#if hasActiveFilters}
          <button type="button" class="reset-filters" transition:fade={{ duration: 150 }} onclick={clearAllFilters}>
            <i class="fa-solid fa-rotate-left"></i> Wyczyść wszystkie filtry
          </button>
        {/if}
      </aside>

      <div class="results-panel">
        <div class="results-summary">
          <span>{filteredReservations.length} {reservationWord(filteredReservations.length)}</span>
        </div>

        {#if filteredReservations.length === 0}
          <div class="empty-state" transition:fade={{ duration: 200 }}>
            <i class="fa-solid fa-calendar-xmark"></i>
            <p>Brak rezerwacji spełniających wybrane filtry.</p>
          </div>
        {:else}
          {#each groups as group (group.key)}
            {#if group.items.length > 0}
              <section class="reservation-section">
                <button type="button" class="section-header" onclick={() => toggleSection(group.key)}>
                  <span class="section-title">
                    <i class={group.icon}></i>
                    {group.label}
                    <span class="section-count">{group.items.length}</span>
                  </span>
                  <i
                    class="fa-solid fa-chevron-down section-chevron"
                    class:collapsed={collapsedSections.has(group.key)}
                  ></i>
                </button>

                {#if !collapsedSections.has(group.key)}
                  <div class="reservation-grid" transition:slide={{ duration: 250, easing: cubicInOut }}>
                    {#each group.items as r (r.id)}
                      {@const mini = buildMiniMonth(r.check_in, r.check_out)}
                      <button
                        type="button"
                        class="reservation-card"
                        class:dimmed={focusedId !== null && focusedId !== r.id}
                        class:focused={focusedId === r.id}
                        onclick={() => openDetail(r)}
                      >
                        <div class="card-top">
                          <div class="card-guest">
                            <span class="guest-name">{r.guest_name}</span>
                            <span class="nights-pill">{nightsBetween(r.check_in, r.check_out)} noc(e)</span>
                          </div>
                        </div>

                        <div class="card-meta">
                          <span><i class="fa-solid fa-location-dot"></i> {r.location_name}</span>
                          <span><i class="fa-solid fa-door-open"></i> {r.room_name}</span>
                        </div>

                        <div class="card-assistant">
                          {#if r.assistant_name}
                            <span class="assistant-avatar" style={`background:${assistantColor(r.assistant_id)}`}>
                              {initials(r.assistant_name)}
                            </span>
                            <span class="assistant-name">{r.assistant_name}</span>
                          {:else}
                            <span class="assistant-avatar assistant-avatar-empty">
                              <i class="fa-solid fa-user-slash"></i>
                            </span>
                            <span class="assistant-name assistant-name-empty">Rezerwacja ręczna</span>
                          {/if}
                        </div>

                        <div class="card-mini-calendar">
                          <span class="mini-cal-label">
                            {mini.label}
                            {#if mini.overflowsAfter}<i class="fa-solid fa-caret-right"></i>{/if}
                          </span>
                          <div class="mini-cal-grid">
                            {#each mini.cells as cell}
                              {#if cell}
                                <span class="mini-cal-cell" class:in-range={cell.inRange}></span>
                              {:else}
                                <span class="mini-cal-cell empty"></span>
                              {/if}
                            {/each}
                          </div>
                        </div>
                      </button>
                    {/each}
                  </div>
                {/if}
              </section>
            {/if}
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>

{#if focusedReservation}
  <button
    type="button"
    class="detail-overlay-backdrop"
    transition:fade={{ duration: 200 }}
    onclick={closeDetail}
    aria-label="Zamknij szczegóły"
  ></button>

  <div class="detail-drawer" transition:fly={{ x: 380, duration: 320, easing: cubicInOut }}>
    <span class="detail-blob" aria-hidden="true"></span>

    <button type="button" class="detail-close" onclick={closeDetail} aria-label="Zamknij">
      <i class="fa-solid fa-xmark"></i>
    </button>

    <div class="detail-header">
      <span class="detail-eyebrow">Rezerwacja #{focusedReservation.id}</span>
      <h2>{focusedReservation.guest_name}</h2>
      <p class="detail-dates">
        {formatDate(focusedReservation.check_in)} – {formatDate(focusedReservation.check_out)}
        · {nightsBetween(focusedReservation.check_in, focusedReservation.check_out)} noc(e)
      </p>
    </div>

    <div class="detail-info-grid">
      <div class="detail-info-item">
        <span class="detail-info-label"><i class="fa-solid fa-location-dot"></i> Lokalizacja</span>
        <span class="detail-info-value">{focusedReservation.location_name}</span>
      </div>
      <div class="detail-info-item">
        <span class="detail-info-label"><i class="fa-solid fa-door-open"></i> Pokój</span>
        <span class="detail-info-value">{focusedReservation.room_name}</span>
      </div>
    </div>

    <div class="detail-assistant-card">
      {#if focusedReservation.assistant_name}
        <span
          class="assistant-avatar assistant-avatar-lg"
          style={`background:${assistantColor(focusedReservation.assistant_id)}`}
        >
          {initials(focusedReservation.assistant_name)}
        </span>
        <div>
          <span class="detail-info-label">Obsłużone przez</span>
          <span class="detail-info-value">{focusedReservation.assistant_name}</span>
        </div>
      {:else}
        <span class="assistant-avatar assistant-avatar-lg assistant-avatar-empty">
          <i class="fa-solid fa-user-slash"></i>
        </span>
        <div>
          <span class="detail-info-label">Obsłużone przez</span>
          <span class="detail-info-value assistant-name-empty">Rezerwacja ręczna (bez asystenta)</span>
        </div>
      {/if}
    </div>

    {#if detailMonth}
      <div class="detail-calendar">
        <div class="filter-calendar-nav">
          <button type="button" class="nav-btn-sm" onclick={detailPrevMonth} aria-label="Poprzedni miesiąc">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="filter-calendar-label">{detailMonth.label}</span>
          <button type="button" class="nav-btn-sm" onclick={detailNextMonth} aria-label="Następny miesiąc">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
        <div class="mini-weekdays">
          {#each weekdayLabels as label}<span>{label}</span>{/each}
        </div>
        {#key detailCursor.getTime()}
          <div class="filter-calendar-weeks" in:fade={{ duration: 180 }}>
            {#each detailMonth.weeks as week}
              <div class="filter-calendar-row">
                {#each week as cell}
                  {#if cell}
                    <span
                      class="filter-day detail-day"
                      class:in-range={cell.iso >= focusedReservation.check_in && cell.iso <= focusedReservation.check_out}
                      class:today={cell.iso === todayIso}
                    >
                      {cell.day}
                    </span>
                  {:else}
                    <span class="filter-day empty"></span>
                  {/if}
                {/each}
              </div>
            {/each}
          </div>
        {/key}
      </div>
    {/if}
  </div>
{/if}

<style>
  .reservations-page {
    width: 100%;
    max-width: min(1600px, 94vw);
    margin: 0 auto;
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
    margin-bottom: 32px;
  }

  .page-header h1 {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .page-header p {
    color: #666;
    font-size: 16px;
  }

  .loading-text {
    color: #666;
  }

  .reservations-layout {
    display: grid;
    grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
    gap: 24px;
    align-items: start;
  }

  /* --- panel filtrów --- */

  .filters-panel {
    display: flex;
    flex-direction: column;
    gap: 22px;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 22px;
    position: sticky;
    top: 20px;
    transition: opacity 0.3s ease;
  }

  .reservations-layout.has-focus .filters-panel {
    opacity: 0.55;
  }

  .filter-block {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .filter-label,
  .filter-label-row .filter-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
  }

  .filter-label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .filter-empty {
    color: #999;
    font-size: 13px;
  }

  .clear-link {
    background: none;
    border: none;
    color: var(--pink);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .search-input {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid var(--border-gray);
    border-radius: 8px;
    padding: 10px 12px;
    transition: border-color 0.2s ease;
  }

  .search-input:focus-within {
    border-color: var(--pink);
  }

  .search-input i {
    color: #999;
    font-size: 13px;
  }

  .search-input input {
    border: none;
    outline: none;
    font-size: 14px;
    font-family: inherit;
    width: 100%;
    color: var(--text-dark);
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--border-gray);
    background: white;
    color: #555;
    border-radius: 999px;
    padding: 7px 13px;
    font-size: 12.5px;
    font-family: inherit;
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.15s ease;
  }

  .chip i {
    font-size: 10px;
    color: var(--pink);
    transition: color 0.2s ease;
  }

  .chip:hover {
    border-color: var(--pink);
    transform: translateY(-1px);
  }

  .chip.active {
    background: var(--pink);
    border-color: var(--pink);
    color: white;
  }

  .chip.active i {
    color: white;
  }

  .filter-calendar {
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 12px;
  }

  .filter-calendar-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .filter-calendar-label {
    font-size: 13px;
    font-weight: 700;
    text-transform: capitalize;
  }

  .nav-btn-sm {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 1px solid var(--border-gray);
    background: white;
    color: #333;
    font-size: 11px;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
  }

  .nav-btn-sm:hover {
    border-color: var(--pink);
    color: var(--pink);
  }

  .mini-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
    margin-bottom: 4px;
  }

  .mini-weekdays span {
    text-align: center;
    font-size: 10px;
    font-weight: 700;
    color: #bbb;
    text-transform: uppercase;
  }

  .filter-calendar-weeks {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .filter-calendar-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
  }

  .filter-day {
    aspect-ratio: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid transparent;
    border-radius: 6px;
    background: none;
    font-size: 11.5px;
    font-family: inherit;
    color: #333;
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  }

  .filter-day.empty {
    cursor: default;
  }

  .filter-day:not(.empty):not(.detail-day):hover {
    background: #fff0f5;
  }

  .filter-day.today {
    border-color: var(--pink);
    font-weight: 700;
  }

  .filter-day.in-range {
    background: #ffd9ea;
  }

  .filter-day.range-edge {
    background: var(--pink);
    color: white;
    font-weight: 700;
  }

  .filter-hint {
    font-size: 12px;
    color: #666;
    font-weight: 600;
  }

  .reset-filters {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px dashed var(--border-gray);
    background: none;
    border-radius: 8px;
    padding: 10px;
    font-size: 12.5px;
    font-weight: 600;
    color: #666;
    font-family: inherit;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
  }

  .reset-filters:hover {
    border-color: var(--pink);
    color: var(--pink);
  }

  /* --- panel wyników --- */

  .results-panel {
    display: flex;
    flex-direction: column;
    gap: 22px;
    min-width: 0;
  }

  .results-summary {
    font-size: 13px;
    font-weight: 600;
    color: #999;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 60px 20px;
    background: white;
    border: 1px dashed var(--border-gray);
    border-radius: 12px;
    color: #999;
  }

  .empty-state i {
    font-size: 28px;
    color: #ddd;
  }

  .reservation-section {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    font-family: inherit;
  }

  .section-title {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-dark);
  }

  .section-title i {
    color: var(--pink);
    font-size: 13px;
  }

  .section-count {
    background: #f2f2f2;
    color: #666;
    font-size: 11px;
    font-weight: 700;
    border-radius: 999px;
    padding: 2px 9px;
  }

  .section-chevron {
    font-size: 12px;
    color: #999;
    transition: transform 0.25s ease;
  }

  .section-chevron.collapsed {
    transform: rotate(-90deg);
  }

  .reservation-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
  }

  .reservation-card {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 12px;
    text-align: left;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 18px;
    font-family: inherit;
    cursor: pointer;
    max-width: 400px;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease, opacity 0.25s ease;
  }

  .reservation-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.06);
    border-color: var(--pink);
  }

  .reservation-card.dimmed {
    opacity: 0.35;
    transform: none;
    box-shadow: none;
  }

  .reservation-card.focused {
    border-color: var(--pink);
    box-shadow: 0 10px 24px rgba(255, 82, 162, 0.18);
  }

  .card-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }

  .card-guest {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .guest-name {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-dark);
  }

  .nights-pill {
    align-self: flex-start;
    background: #fff0f5;
    color: var(--pink);
    font-size: 11px;
    font-weight: 700;
    border-radius: 999px;
    padding: 2px 9px;
  }

  .card-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .card-meta span {
    font-size: 12.5px;
    color: #666;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .card-meta i {
    color: var(--pink);
    font-size: 11px;
    width: 12px;
  }

  .card-assistant {
    display: flex;
    align-items: center;
    gap: 8px;
    padding-top: 4px;
    border-top: 1px dashed #eee;
  }

  .assistant-avatar {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    color: white;
    font-size: 10.5px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .assistant-avatar-lg {
    width: 40px;
    height: 40px;
    font-size: 14px;
  }

  .assistant-avatar-empty {
    background: #eee;
    color: #999;
  }

  .assistant-name {
    font-size: 12.5px;
    font-weight: 600;
    color: #444;
  }

  .assistant-name-empty {
    color: #999;
    font-style: italic;
    font-weight: 500;
  }

  .card-mini-calendar {
    margin-top: 2px;
    padding-top: 12px;
    border-top: 1px solid #f2f2f2;
  }

  .mini-cal-label {
    display: block;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #bbb;
    margin-bottom: 6px;
  }

  .mini-cal-label i {
    color: var(--pink);
    margin-left: 4px;
  }

  .mini-cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 2px;
  }

  .mini-cal-cell {
    aspect-ratio: 1;
    border-radius: 2px;
    background: #f5f5f5;
  }

  .mini-cal-cell.empty {
    background: none;
  }

  .mini-cal-cell.in-range {
    background: var(--pink);
  }

  /* --- overlay szczegółów --- */

  .detail-overlay-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(20, 20, 20, 0.35);
    border: none;
    z-index: 950;
    cursor: default;
  }

  .detail-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(420px, 100vw);
    background: white;
    box-shadow: -20px 0 40px rgba(0, 0, 0, 0.12);
    z-index: 951;
    padding: 30px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .detail-blob {
    position: absolute;
    top: -80px;
    right: -80px;
    width: 250px;
    height: 250px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(30px);
    opacity: 0.25;
    pointer-events: none;
  }

  .detail-close {
    align-self: flex-end;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    border: 1px solid var(--border-gray);
    background: white;
    color: #666;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
    position: relative;
    z-index: 1;
  }

  .detail-close:hover {
    border-color: var(--pink);
    color: var(--pink);
  }

  .detail-header {
    position: relative;
    z-index: 1;
  }

  .detail-eyebrow {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
  }

  .detail-header h2 {
    font-size: 26px;
    font-weight: 700;
    margin: 6px 0;
  }

  .detail-dates {
    color: #666;
    font-size: 14px;
  }

  .detail-info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .detail-info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    background: #fafafa;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 12px 14px;
  }

  .detail-info-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #999;
    display: block;
  }

  .detail-info-label i {
    color: var(--pink);
    margin-right: 5px;
  }

  .detail-info-value {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dark);
  }

  .detail-assistant-card {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #fafafa;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 14px 16px;
  }

  .detail-assistant-card > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .detail-calendar {
    border: 1px solid #eaeaea;
    border-radius: 10px;
    padding: 14px;
  }

  .detail-day {
    cursor: default;
  }

  @media (max-width: 900px) {
    .reservations-layout {
      grid-template-columns: 1fr;
    }

    .filters-panel {
      position: static;
    }
  }

  @media (max-width: 640px) {
    .page-header h1 {
      font-size: 28px;
    }

    .detail-drawer {
      width: 100vw;
      padding: 22px;
    }

    .detail-info-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
