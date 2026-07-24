import axios from "axios";

/**
 * Central Axios instance. Base URL is configurable at runtime via the Settings
 * page (persisted to localStorage) and falls back to the dev proxy target.
 */
const STORAGE_KEY = "spandana-api-base";

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  }
  return "http://localhost:8000";
}

export function setApiBase(url: string): void {
  window.localStorage.setItem(STORAGE_KEY, url);
  api.defaults.baseURL = url;
}

export const api = axios.create({
  baseURL: getApiBase(),
  timeout: 4000,
  headers: { "Content-Type": "application/json" },
});
