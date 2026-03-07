/**
 * SAR Guardian — Axios API Client
 * No auth interceptor — backend endpoints are public.
 */

import axios from "axios";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export { api };
export default api;
