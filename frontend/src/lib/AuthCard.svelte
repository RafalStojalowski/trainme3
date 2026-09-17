<script>
  let { onLoggedIn } = $props();

  let mode = $state("login"); // "login" | "register"
  let email = $state("");
  let password = $state("");
  let fullName = $state("");
  let confirmPassword = $state("");
  let submitting = $state(false);
  let error = $state("");

  function toggleMode() {
    mode = mode === "login" ? "register" : "login";
    error = "";
  }

  async function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    error = "";
    submitting = true;

    try {
      const res = await postJson("/api/auth/login", { email, password });
      if (!res.ok) {
        error = "Nieprawidłowy e-mail lub hasło.";
        return;
      }
      onLoggedIn(await res.json());
    } catch {
      error = "Nie udało się połączyć z serwerem.";
    } finally {
      submitting = false;
    }
  }

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    error = "";

    if (password !== confirmPassword) {
      error = "Hasła nie są takie same.";
      return;
    }

    submitting = true;

    try {
      const registerRes = await postJson("/api/auth/register", {
        email,
        full_name: fullName,
        password,
      });

      if (!registerRes.ok) {
        error =
          registerRes.status === 409
            ? "Konto z tym adresem e-mail już istnieje."
            : registerRes.status === 422
              ? "Sprawdź, czy e-mail i hasło (min. 8 znaków) są poprawne."
              : "Nie udało się utworzyć konta. Spróbuj ponownie.";
        return;
      }

      const loginRes = await postJson("/api/auth/login", { email, password });
      if (!loginRes.ok) {
        error = "Konto utworzone, ale logowanie się nie powiodło. Spróbuj zalogować się ręcznie.";
        return;
      }

      onLoggedIn(await loginRes.json());
    } catch {
      error = "Nie udało się połączyć z serwerem.";
    } finally {
      submitting = false;
    }
  }
</script>

<div class="auth-card" class:expanded={mode === "register"}>
  <div class="brand-panel">
    <div class="brand-logo">Train<span class="highlight">Me</span></div>

    <div class="login-fields" inert={mode !== "login"}>
      <h1 class="auth-title">Zaloguj się do <span class="highlight">Train.me</span></h1>
      <p class="auth-subtitle">Miło Cię znowu widzieć.</p>

      {#if error && mode === "login"}
        <div class="form-error">{error}</div>
      {/if}

      <form onsubmit={handleLoginSubmit}>
        <div class="form-field">
          <label for="login-email">Adres e-mail</label>
          <input
            id="login-email"
            class="field-input"
            type="email"
            bind:value={email}
            required
            autocomplete="email"
          />
        </div>
        <div class="form-field">
          <label for="login-password">Hasło</label>
          <input
            id="login-password"
            class="field-input"
            type="password"
            bind:value={password}
            required
            minlength="8"
            autocomplete="current-password"
          />
        </div>
        <button class="btn-primary" type="submit" disabled={submitting || mode !== "login"}>
          {submitting ? "Chwila..." : "Zaloguj się"}
        </button>
      </form>

      <button class="btn-link" type="button" onclick={toggleMode}>Stwórz nowe konto</button>
    </div>
  </div>

  <div class="form-panel" inert={mode !== "register"}>
    <div class="register-fields">
      <h1 class="auth-title">Dołącz do <span class="highlight">Train.me</span></h1>
      <p class="auth-subtitle">Załóż konto w kilka sekund.</p>

      {#if error && mode === "register"}
        <div class="form-error">{error}</div>
      {/if}

      <form onsubmit={handleRegisterSubmit}>
        <div class="form-field">
          <label for="register-email">Adres e-mail</label>
          <input
            id="register-email"
            class="field-input"
            type="email"
            bind:value={email}
            required={mode === "register"}
            autocomplete="email"
          />
        </div>
        <div class="form-field">
          <label for="register-fullname">Imię i nazwisko</label>
          <input
            id="register-fullname"
            class="field-input"
            type="text"
            bind:value={fullName}
            required={mode === "register"}
            autocomplete="name"
          />
        </div>
        <div class="form-field">
          <label for="register-password">Hasło</label>
          <input
            id="register-password"
            class="field-input"
            type="password"
            bind:value={password}
            required={mode === "register"}
            minlength="8"
            autocomplete="new-password"
          />
        </div>
        <div class="form-field">
          <label for="register-confirm-password">Powtórz hasło</label>
          <input
            id="register-confirm-password"
            class="field-input"
            type="password"
            bind:value={confirmPassword}
            required={mode === "register"}
            minlength="8"
            autocomplete="new-password"
          />
        </div>
        <button class="btn-primary" type="submit" disabled={submitting || mode !== "register"}>
          {submitting ? "Chwila..." : "Zarejestruj się"}
        </button>
      </form>

      <button class="btn-link" type="button" onclick={toggleMode}>Masz już konto? Zaloguj się</button>
    </div>
  </div>
</div>

<style>
  .auth-card {
    display: flex;
    align-items: stretch;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    padding: 72px 64px;
    width: 460px;
    max-width: 100%;
    overflow: hidden;
    transition: width 0.7s ease, padding 0.7s ease;
  }

  .auth-card.expanded {
    width: 820px;
  }

  .brand-panel {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    transition: width 0.7s ease, align-items 0.7s ease;
  }

  .auth-card.expanded .brand-panel {
    width: 260px;
    align-items: flex-start;
  }

  .brand-logo {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
    transition: font-size 0.7s ease;
  }

  .auth-card.expanded .brand-logo {
    font-size: 52px;
  }

  .login-fields {
    width: 100%;
    margin-top: 24px;
    opacity: 1;
    max-height: 500px;
    overflow: hidden;
    transition: opacity 0.45s ease, max-height 0.45s ease, margin-top 0.45s ease;
  }

  .auth-card.expanded .login-fields {
    opacity: 0;
    max-height: 0;
    margin-top: 0;
    pointer-events: none;
  }

  .form-panel {
    flex-shrink: 0;
    width: 0;
    opacity: 0;
    overflow: hidden;
    margin-left: 0;
    transition: width 0.7s ease, opacity 0.45s ease 0.15s, margin-left 0.7s ease;
  }

  .auth-card.expanded .form-panel {
    width: 380px;
    opacity: 1;
    margin-left: 48px;
  }

  .register-fields {
    width: 380px;
  }

  .auth-title {
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 10px;
  }

  .auth-subtitle {
    color: #666;
    margin-bottom: 30px;
    font-size: 14px;
  }

  .form-field {
    text-align: left;
    margin-bottom: 18px;
  }

  .form-field label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #333;
    margin-bottom: 6px;
  }

  .field-input {
    width: 100%;
    padding: 15px;
    border: 1px solid var(--border-gray);
    border-radius: 8px;
    font-size: 16px;
  }

  .field-input:focus {
    outline: none;
    border-color: var(--pink);
    box-shadow: 0 0 0 1px var(--pink);
  }

  .btn-primary {
    width: 100%;
    background: black;
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 6px;
    font-size: 16px;
    cursor: pointer;
    margin-top: 6px;
  }

  .btn-primary:hover:not(:disabled) {
    background: #333;
  }

  .btn-primary:disabled {
    background: #999;
    cursor: not-allowed;
  }

  .btn-link {
    display: block;
    margin: 20px auto 0;
    background: none;
    border: none;
    text-decoration: underline;
    cursor: pointer;
    color: #666;
    font-size: 14px;
  }

  .btn-link:hover {
    color: var(--pink);
  }

  .form-error {
    background: #fff0f5;
    color: #c0175a;
    border: 1px solid #ffd3e6;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 14px;
    margin-bottom: 20px;
    text-align: left;
  }

  @media (max-width: 860px) {
    .auth-card,
    .auth-card.expanded {
      width: 100%;
      flex-direction: column;
      padding: 36px 24px;
    }

    .auth-card.expanded .brand-panel {
      width: 100%;
      align-items: center;
    }

    .auth-card.expanded .form-panel {
      width: 100%;
      margin-left: 0;
      margin-top: 24px;
    }

    .register-fields {
      width: 100%;
    }
  }
</style>
