<script>
  import { API_BASE } from "./lib/api.js";
  import AuthCard from "./lib/AuthCard.svelte";
  import AssistantsPage from "./lib/AssistantsPage.svelte";
  import LocationsPage from "./lib/LocationsPage.svelte";
  import CalendarPage from "./lib/CalendarPage.svelte";
  import ReservationsPage from "./lib/ReservationsPage.svelte";

  let user = $state(null);
  let checkingSession = $state(true);

  const pathByView = {
    dashboard: "/",
    assistants: "/assistants",
    locations: "/locations",
    calendar: "/calendar",
    reservations: "/reservations",
  };
  const viewByPath = {
    "/": "dashboard",
    "/assistants": "assistants",
    "/locations": "locations",
    "/calendar": "calendar",
    "/reservations": "reservations",
  };

  function viewFromPath(pathname) {
    return viewByPath[pathname] ?? "dashboard";
  }

  let view = $state(viewFromPath(window.location.pathname));

  function navigate(nextView) {
    view = nextView;
    const path = pathByView[nextView] ?? "/";
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
  }

  window.addEventListener("popstate", () => {
    view = viewFromPath(window.location.pathname);
  });

  async function loadSession() {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, { credentials: "include" });
      if (res.ok) {
        user = await res.json();
      }
    } finally {
      checkingSession = false;
    }
  }

  async function handleLogout() {
    await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
    user = null;
  }

  loadSession();

  let menuOpen = $state(false);

  function toggleMenu() {
    menuOpen = !menuOpen;
  }

  function closeMenu() {
    menuOpen = false;
  }

  let authCardKey = $state(0);

  function goHome() {
    closeMenu();
    navigate("dashboard");
    // Wymusza remount AuthCard, resetując go z powrotem do widoku logowania.
    authCardKey++;
  }

  const features = [
    {
      title: "Zarządzanie asystentami",
      description: "Konfiguruj wirtualnych konsultantów, ich wiedzę i sposób odpowiadania gościom.",
      action: () => navigate("assistants"),
    },
    {
      title: "Lokalizacje",
      description: "Przeglądaj i zarządzaj obiektami dostępnymi do wynajęcia.",
      action: () => navigate("locations"),
    },
    {
      title: "Rezerwacje",
      description: "Przeglądaj i obsługuj rezerwacje utworzone przez gości i wirtualnych konsultantów.",
      action: () => navigate("reservations"),
    },
  ];

  const disabledFeature = {
    title: "Zarządzanie użytkownikami",
    description: "Dostępne tylko dla administratorów systemu.",
  };

  function displayName(u) {
    if (u.full_name && u.full_name.trim()) return u.full_name;
    return u.email.split("@")[0];
  }

  const weekdayLabels = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"];
  const monthNames = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
  ];

  function buildCalendar(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const startWeekday = (new Date(year, month, 1).getDay() + 6) % 7; // Pn = 0
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells = [];
    for (let i = 0; i < startWeekday; i++) cells.push(null);
    for (let day = 1; day <= daysInMonth; day++) cells.push(day);
    while (cells.length % 7 !== 0) cells.push(null);

    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));

    return { weeks, monthLabel: `${monthNames[month]} ${year}` };
  }

  const today = new Date();
  const calendar = buildCalendar(today);
  const todayNumber = today.getDate();
</script>

<header>
  <button class="logo" onclick={goHome}>Train<span class="highlight">Me</span></button>
  {#if user}
    <div class="user-menu">
      <button class="user-menu-trigger" onclick={toggleMenu}>
        Witaj, <strong>{displayName(user)}</strong>
        <i class="fa-solid fa-chevron-down" class:open={menuOpen}></i>
      </button>

      {#if menuOpen}
        <button class="user-menu-overlay" aria-label="Zamknij menu" onclick={closeMenu}></button>
        <div class="user-menu-dropdown">
          <button class="user-menu-item" onclick={closeMenu}>Zarządzaj kontem</button>
          <button
            class="user-menu-item"
            onclick={() => {
              closeMenu();
              handleLogout();
            }}
          >
            Wyloguj się
          </button>
        </div>
      {/if}
    </div>
  {/if}
</header>

<main class:dashboard-active={!!user}>
  {#if !checkingSession}
    {#if user && view === "assistants"}
      <AssistantsPage onBack={goHome} />
    {:else if user && view === "locations"}
      <LocationsPage onBack={goHome} />
    {:else if user && view === "calendar"}
      <CalendarPage onBack={goHome} />
    {:else if user && view === "reservations"}
      <ReservationsPage onBack={goHome} />
    {:else if user}
      <div class="dashboard">
        <div class="dashboard-header">
          <h1>Witaj z powrotem, <span class="highlight">{displayName(user).split(" ")[0]}</span></h1>
          <p>Zarządzaj lokalizacjami, wirtualnymi konsultantami i rezerwacjami w jednym miejscu.</p>
        </div>

        <div class="feature-layout">
          <div class="feature-list">
            {#each features as feature}
              <button class="feature-tile" onclick={feature.action}>
                <span class="tile-blob" aria-hidden="true"></span>
                <div class="tile-text">
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </button>
            {/each}

            <div class="feature-tile disabled">
              <span class="tile-blob" aria-hidden="true"></span>
              <div class="tile-text">
                <h3>{disabledFeature.title}</h3>
                <p>{disabledFeature.description}</p>
              </div>
              <span class="feature-badge">Niedostępne</span>
            </div>
          </div>

          <button class="calendar-tile" onclick={() => navigate("calendar")}>
            <span class="tile-blob tile-blob-secondary" aria-hidden="true"></span>
            <div class="calendar-tile-header">
              <span class="tile-blob" aria-hidden="true"></span>
              <div class="tile-text">
                <h3>Kalendarz</h3>
                <p>{calendar.monthLabel}</p>
              </div>
            </div>

            <div class="mini-calendar">
              <div class="mini-calendar-row mini-calendar-weekdays">
                {#each weekdayLabels as label}
                  <span>{label}</span>
                {/each}
              </div>
              {#each calendar.weeks as week}
                <div class="mini-calendar-row">
                  {#each week as day}
                    <span class="mini-calendar-day" class:today={day === todayNumber}>{day ?? ""}</span>
                  {/each}
                </div>
              {/each}
            </div>

            <span class="calendar-cta">Przejdź do kalendarza <i class="fa-solid fa-arrow-right"></i></span>
          </button>
        </div>
      </div>
    {:else}
      {#key authCardKey}
        <AuthCard onLoggedIn={(loggedInUser) => (user = loggedInUser)} />
      {/key}
    {/if}
  {/if}
</main>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 50px;
    background-color: white;
    border-bottom: 1px solid #eaeaea;
    position: sticky;
    top: 0;
  }

  .logo {
    background: none;
    border: none;
    padding: 0;
    font-family: inherit;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
    cursor: pointer;
    color: var(--text-dark);
  }

  .user-menu {
    position: relative;
  }

  .user-menu-trigger {
    display: flex;
    align-items: center;
    gap: 10px;
    background: none;
    border: none;
    font-size: 14px;
    color: #333;
    cursor: pointer;
    padding: 6px 0;
  }

  .user-menu-trigger i {
    font-size: 11px;
    color: #999;
    transition: transform 0.2s ease;
  }

  .user-menu-trigger i.open {
    transform: rotate(180deg);
  }

  .user-menu-overlay {
    position: fixed;
    inset: 0;
    background: transparent;
    border: none;
    z-index: 900;
    cursor: default;
  }

  .user-menu-dropdown {
    position: absolute;
    top: calc(100% + 10px);
    right: 0;
    min-width: 200px;
    background: white;
    border: 1px solid #eaeaea;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 901;
  }

  .user-menu-item {
    background: none;
    border: none;
    text-align: left;
    padding: 10px 12px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    color: var(--pink);
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .user-menu-item:hover {
    background-color: #fff0f5;
  }

  main {
    min-height: calc(100vh - 82px);
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 60px clamp(20px, 4vw, 60px);
  }

  main.dashboard-active {
    align-items: flex-start;
    text-align: left;
  }

  .dashboard {
    width: 100%;
    max-width: min(1600px, 94vw);
    margin: 0 auto;
  }

  .dashboard-header h1 {
    font-size: 40px;
    font-weight: 700;
    margin-bottom: 10px;
  }

  .dashboard-header p {
    color: #666;
    font-size: 16px;
    margin-bottom: 40px;
  }

  .feature-layout {
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 24px;
    align-items: stretch;
  }

  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .feature-tile,
  .calendar-tile {
    position: relative;
    border: 1px solid #eaeaea;
    background-color: white;
    border-radius: 12px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    overflow: hidden;
  }

  .feature-tile:not(.disabled),
  .calendar-tile {
    cursor: pointer;
  }

  .feature-tile:not(.disabled):hover,
  .calendar-tile:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
  }

  .feature-tile {
    display: flex;
    align-items: center;
    padding: 26px 30px;
    flex: 1;
    width: 100%;
    font: inherit;
    text-align: left;
  }

  .tile-blob {
    position: absolute;
    top: -25px;
    left: -25px;
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: var(--pink);
    filter: blur(20px);
    opacity: 0.35;
    pointer-events: none;
    user-select: none;
  }

  .tile-text {
    position: relative;
    z-index: 1;
  }

  .tile-text h3 {
    font-size: 19px;
    margin-bottom: 6px;
  }

  .tile-text p {
    color: #666;
    font-size: 14px;
  }

  .feature-tile.disabled {
    opacity: 0.55;
    filter: grayscale(1);
    cursor: not-allowed;
  }

  .feature-badge {
    position: absolute;
    top: 18px;
    right: 20px;
    z-index: 1;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #999;
    background: #f2f2f2;
    padding: 4px 10px;
    border-radius: 999px;
  }

  .calendar-tile {
    padding: 30px;
    display: flex;
    flex-direction: column;
    width: 100%;
    font: inherit;
    text-align: left;
    color: inherit;
  }

  .calendar-tile-header {
    position: relative;
    display: flex;
    align-items: center;
    margin-bottom: 24px;
  }

  .calendar-tile-header .tile-blob {
    width: 140px;
    height: 140px;
    top: -40px;
    left: -40px;
  }

  .tile-blob-secondary {
    top: auto;
    left: auto;
    bottom: -70px;
    right: -70px;
    width: 220px;
    height: 220px;
    opacity: 0.12;
  }

  .mini-calendar {
    position: relative;
    z-index: 1;
    flex: 1;
  }

  .mini-calendar-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 6px;
  }

  .mini-calendar-weekdays span {
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: #999;
    text-transform: uppercase;
  }

  .mini-calendar-day {
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1;
    border-radius: 8px;
    font-size: 13px;
    color: #333;
  }

  .mini-calendar-day.today {
    background: var(--pink);
    color: white;
    font-weight: 700;
  }

  .calendar-cta {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 24px;
    color: var(--pink);
    font-size: 14px;
    font-weight: 600;
  }

  @media (max-width: 860px) {
    .feature-layout {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    header {
      flex-direction: column;
      gap: 15px;
      padding: 15px 20px;
    }

    .user-menu-dropdown {
      right: auto;
      left: 50%;
      transform: translateX(-50%);
    }

    .dashboard-header h1 {
      font-size: 28px;
    }
  }
</style>
