<script>
  import { fly } from "svelte/transition";
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

  let cursor = $state(new Date(today.getFullYear(), today.getMonth(), 1));
  let selectedDate = $state(todayIso);
  let highlightedReservationId = $state(null);
  let pickerOpen = $state(false);
  let pickerMode = $state("month"); // "month" | "year"
  let direction = $state(1); // 1 = w przód (kalendarz wjeżdża z prawej), -1 = w tył (z lewej)
  let weeksViewportWidth = $state(0);

  const yearOptions = Array.from({ length: 11 }, (_, i) => today.getFullYear() - 5 + i);

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

  function buildMonth(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const startWeekday = (new Date(year, month, 1).getDay() + 6) % 7; // Pn = 0
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) {
      cells.push({ day, iso: toISODate(new Date(year, month, day)) });
    }
    while (cells.length % 7 !== 0) cells.push(null);

    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

    return { weeks, monthLabel: `${monthNames[month]} ${year}` };
  }

  let month = $derived(buildMonth(cursor));

  function reservationsForDate(iso) {
    return reservations.filter((r) => r.check_in <= iso && iso <= r.check_out);
  }

  let monthReservations = $derived.by(() => {
    const year = cursor.getFullYear();
    const monthIndex = cursor.getMonth();
    const firstIso = toISODate(new Date(year, monthIndex, 1));
    const lastIso = toISODate(new Date(year, monthIndex + 1, 0));
    return reservations
      .filter((r) => r.check_in <= lastIso && r.check_out >= firstIso)
      .sort((a, b) => (a.check_in < b.check_in ? -1 : a.check_in > b.check_in ? 1 : 0));
  });

  let highlightedReservation = $derived(
    reservations.find((r) => r.id === highlightedReservationId) ?? null,
  );

  function setCursor(newCursor) {
    const oldTime = cursor.getTime();
    const newTime = newCursor.getTime();
    if (newTime !== oldTime) {
      direction = newTime > oldTime ? 1 : -1;
    }
    cursor = newCursor;
  }

  function prevMonth() {
    setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1));
  }

  function nextMonth() {
    setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1));
  }

  function goToday() {
    setCursor(new Date(today.getFullYear(), today.getMonth(), 1));
    selectedDate = todayIso;
  }

  function setMonthYear(monthIndex, year) {
    setCursor(new Date(year, monthIndex, 1));
    pickerOpen = false;
  }

  function selectDay(iso) {
    if (!iso) return;
    selectedDate = iso;
    highlightedReservationId = null;
  }

  function highlightReservation(reservation) {
    highlightedReservationId = reservation.id;
    selectedDate = reservation.check_in;
    const [year, monthNumber] = reservation.check_in.split("-").map(Number);
    setCursor(new Date(year, monthNumber - 1, 1));
  }

  function formatDate(iso) {
    const [year, month, day] = iso.split("-");
    return `${day}.${month}.${year}`;
  }

  function isSameDate(iso, targetIso) {
    return iso === targetIso;
  }

  function isInHighlightedReservation(iso) {
    return highlightedReservation ? highlightedReservation.check_in <= iso && iso <= highlightedReservation.check_out : false;
  }
</script>

<div class="calendar-page">
  <button class="back-link" onclick={onBack}><i class="fa-solid fa-arrow-left"></i> Wróć do panelu</button>

  <div class="page-header">
    <div class="page-header-text">
      <h1>Kalendarz <span class="highlight">rezerwacji</span></h1>
      <p>Przeglądaj rezerwacje we wszystkich lokalizacjach i pokojach.</p>
    </div>
  </div>

  {#if loading}
    <p class="loading-text">Ładowanie...</p>
  {:else}
    <div class="calendar-layout">
      <div class="calendar-detail">
        <div class="detail-section">
          <h4>Rezerwacje – {month.monthLabel}</h4>
          {#if monthReservations.length === 0}
            <p class="detail-placeholder">Brak rezerwacji w tym miesiącu.</p>
          {:else}
            <div class="reservation-list">
              {#each monthReservations as reservation}
                <button
                  class="reservation-item reservation-item-clickable"
                  class:reservation-item-active={highlightedReservationId === reservation.id}
                  onclick={() => highlightReservation(reservation)}
                >
                  <div class="reservation-item-header">
                    <span class="reservation-guest">{reservation.guest_name}</span>
                    <span class="reservation-dates">
                      {formatDate(reservation.check_in)} – {formatDate(reservation.check_out)}
                    </span>
                  </div>
                  <span class="reservation-room">
                    <i class="fa-solid fa-door-open"></i> {reservation.room_name}
                  </span>
                  <span class="reservation-location">
                    <i class="fa-solid fa-location-dot"></i> {reservation.location_name}
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="calendar-card">
        <div class="calendar-nav">
          <button class="nav-btn" onclick={prevMonth} aria-label="Poprzedni miesiąc">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <div class="calendar-nav-title">
            <button class="month-year-toggle" onclick={() => (pickerOpen = !pickerOpen)}>
              <h2>{month.monthLabel}</h2>
              <i class="fa-solid fa-chevron-down" class:open={pickerOpen}></i>
            </button>
            <button class="today-link" onclick={goToday}>Dziś</button>

            {#if pickerOpen}
              <button
                class="picker-overlay"
                aria-label="Zamknij wybór miesiąca"
                onclick={() => (pickerOpen = false)}
              ></button>
              <div class="month-year-picker">
                <div class="picker-tabs">
                  <button
                    class="picker-tab"
                    class:active={pickerMode === "month"}
                    onclick={() => (pickerMode = "month")}
                  >
                    Miesiąc
                  </button>
                  <button
                    class="picker-tab"
                    class:active={pickerMode === "year"}
                    onclick={() => (pickerMode = "year")}
                  >
                    Rok
                  </button>
                </div>

                <div class="picker-tiles">
                  {#if pickerMode === "month"}
                    {#each monthNames as name, i}
                      <button
                        class="picker-tile"
                        class:active={cursor.getMonth() === i}
                        onclick={() => setMonthYear(i, cursor.getFullYear())}
                      >
                        {name}
                      </button>
                    {/each}
                  {:else}
                    {#each yearOptions as year}
                      <button
                        class="picker-tile"
                        class:active={cursor.getFullYear() === year}
                        onclick={() => setMonthYear(cursor.getMonth(), year)}
                      >
                        {year}
                      </button>
                    {/each}
                  {/if}
                </div>
              </div>
            {/if}
          </div>
          <button class="nav-btn" onclick={nextMonth} aria-label="Następny miesiąc">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>

        <div class="calendar-grid-weekdays">
          {#each weekdayLabels as label}
            <span>{label}</span>
          {/each}
        </div>

        <div class="calendar-weeks-viewport" bind:clientWidth={weeksViewportWidth}>
          {#key `${cursor.getFullYear()}-${cursor.getMonth()}`}
            <div
              class="calendar-weeks"
              in:fly={{ x: direction * weeksViewportWidth, duration: 300, easing: cubicInOut, opacity: 1 }}
              out:fly={{ x: direction * -weeksViewportWidth, duration: 300, easing: cubicInOut, opacity: 1 }}
            >
              {#each month.weeks as week}
                <div class="calendar-grid-row">
                  {#each week as cell}
                    {#if cell}
                      {@const dayReservations = reservationsForDate(cell.iso)}
                      <button
                        class="calendar-day"
                        class:today={isSameDate(cell.iso, todayIso)}
                        class:selected={isSameDate(cell.iso, selectedDate)}
                        class:range-highlight={isInHighlightedReservation(cell.iso)}
                        class:has-reservations={dayReservations.length > 0}
                        onclick={() => selectDay(cell.iso)}
                      >
                        <span class="calendar-day-number">{cell.day}</span>
                        {#if dayReservations.length > 0}
                          <span class="calendar-day-dots">
                            {#each dayReservations.slice(0, 3) as _ignored}
                              <span class="calendar-day-dot"></span>
                            {/each}
                          </span>
                        {/if}
                      </button>
                    {:else}
                      <span class="calendar-day empty"></span>
                    {/if}
                  {/each}
                </div>
              {/each}
            </div>
          {/key}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .calendar-page {
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

  .loading-text {
    color: #666;
  }

  .calendar-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.7fr);
    gap: 24px;
    align-items: start;
  }

  .calendar-card {
    display: flex;
    flex-direction: column;
    gap: 4px;
    height: max(320px, calc(100vh - 360px));
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 20px;
  }

  .calendar-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .calendar-nav-title {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }

  .month-year-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    font: inherit;
    cursor: pointer;
  }

  .month-year-toggle i {
    font-size: 11px;
    color: #999;
    transition: transform 0.2s ease;
  }

  .month-year-toggle i.open {
    transform: rotate(180deg);
  }

  .calendar-nav-title h2 {
    font-size: 20px;
    font-weight: 700;
    text-transform: capitalize;
  }

  .today-link {
    background: none;
    border: none;
    color: var(--pink);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .picker-overlay {
    position: fixed;
    inset: 0;
    background: transparent;
    border: none;
    z-index: 20;
    cursor: default;
  }

  .month-year-picker {
    position: absolute;
    top: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 360px;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    padding: 18px;
    z-index: 21;
  }

  .picker-tabs {
    display: flex;
    background: #f2f2f2;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
  }

  .picker-tab {
    flex: 1;
    background: none;
    border: none;
    border-radius: 8px;
    padding: 10px 0;
    font-size: 15px;
    font-weight: 600;
    color: #666;
    font-family: inherit;
    cursor: pointer;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .picker-tab.active {
    background: white;
    color: var(--text-dark);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .picker-tiles {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    max-height: 300px;
    overflow-y: auto;
  }

  .picker-tile {
    border: none;
    border-radius: 8px;
    padding: 14px 6px;
    font-size: 15px;
    font-family: inherit;
    color: #333;
    background: white;
    cursor: pointer;
    text-transform: capitalize;
    transition: background-color 0.2s ease, color 0.2s ease;
  }

  .picker-tile:hover {
    background: #ffe3f0;
  }

  .picker-tile.active {
    background: var(--pink);
    color: white;
  }

  .nav-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1px solid var(--border-gray);
    background: white;
    color: #333;
    cursor: pointer;
    transition: border-color 0.2s ease, color 0.2s ease;
  }

  .nav-btn:hover {
    border-color: var(--pink);
    color: var(--pink);
  }

  .calendar-grid-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 6px;
  }

  .calendar-grid-weekdays span {
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: #999;
    text-transform: uppercase;
  }

  .calendar-weeks-viewport {
    position: relative;
    flex: 1;
    overflow: hidden;
  }

  .calendar-weeks {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .calendar-grid-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    flex: 1;
  }

  .calendar-day {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    height: 100%;
    border-radius: 8px;
    border: 1px solid transparent;
    background: none;
    font-size: 13px;
    color: #333;
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .calendar-day.empty {
    cursor: default;
  }

  .calendar-day:not(.empty):hover {
    background-color: #fff0f5;
  }

  .calendar-day.today {
    border-color: var(--pink);
    font-weight: 700;
  }

  .calendar-day.range-highlight {
    background-color: #ffd9ea;
  }

  .calendar-day.selected {
    background-color: var(--pink);
    color: white;
  }

  .calendar-day.selected.today {
    border-color: transparent;
  }

  .calendar-day-dots {
    display: flex;
    gap: 3px;
  }

  .calendar-day-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--pink);
  }

  .calendar-day.selected .calendar-day-dot {
    background: white;
  }

  .calendar-detail {
    display: flex;
    flex-direction: column;
    gap: 24px;
    height: max(320px, calc(100vh - 360px));
    overflow-y: auto;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 12px;
    padding: 24px;
  }

  .detail-section h4 {
    display: block;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
    margin-bottom: 12px;
  }

  .detail-placeholder {
    color: #999;
    font-size: 14px;
  }

  .reservation-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .reservation-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    background: #fafafa;
    border: 1px solid #eaeaea;
    border-radius: 8px;
    padding: 12px 14px;
    text-align: left;
  }

  .reservation-item-clickable {
    width: 100%;
    font: inherit;
    cursor: pointer;
    transition: border-color 0.2s ease;
  }

  .reservation-item-active {
    border-color: var(--pink);
    background: #fff0f5;
  }

  .reservation-item-clickable:hover {
    border-color: var(--pink);
  }

  .reservation-item-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }

  .reservation-guest {
    font-size: 14px;
    font-weight: 700;
    color: var(--text-dark);
  }

  .reservation-dates {
    font-size: 12px;
    font-weight: 600;
    color: #666;
  }

  .reservation-room,
  .reservation-location {
    font-size: 12px;
    color: #666;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .reservation-room i,
  .reservation-location i {
    color: var(--pink);
    font-size: 11px;
  }

  @media (max-width: 900px) {
    .calendar-layout {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .calendar-card {
      padding: 20px;
    }

    .page-header-text h1 {
      font-size: 28px;
    }
  }
</style>
