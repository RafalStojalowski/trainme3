// Backend base URL. Pusty string = wywołania względne (lokalny dev, proxy w vite.config.js).
// Na Cloudflare ustaw zmienną budowania VITE_API_URL na publiczny adres backendu (Render).
export const API_BASE = import.meta.env.VITE_API_URL ?? "";
