const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
  .replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const api = {
  async get<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'GET' })
  },
  async post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, init)
  } catch {
    throw new ApiError(
      `Cannot reach the API at ${apiBaseUrl}. Start the FastAPI backend and check its CORS settings.`,
      0,
    )
  }

  const text = await response.text()
  let result: unknown
  try {
    result = text ? JSON.parse(text) : null
  } catch {
    result = text
  }
  if (!response.ok) {
    const detail =
      typeof result === 'object' && result !== null && 'detail' in result
        ? String((result as { detail: unknown }).detail)
        : typeof result === 'string' && result
          ? result
          : response.statusText
    throw new ApiError(`API request failed (${response.status}): ${detail}`, response.status)
  }
  return result as T
}

export type HomeSummary = {
  user_id: number
  balance_credits: number
  credits_this_week: number
  co2_saved_kg: number
  distance_km: number
}

export type Trip = {
  id: number
  user_id: number
  date: string
  distance_km: number
  transport_modes: string[]
  credits: number
  credits_earned?: number | null
  co2_emitted_kg?: number | null
  co2_saved_kg?: number | null
}

export type SeriesPoint = { label: string; credits: number; trips: number }

export type TripStats = {
  user_id: number
  total_trips: number
  total_credits: number
  total_distance_km: number
  total_co2_kg: number
  daily: SeriesPoint[]
  weekly: SeriesPoint[]
  monthly: SeriesPoint[]
}

export type WalletHistory = {
  kind: string
  date: string
  title: string
  amount: number
}

export type WalletSummary = {
  user_id: number
  balance_credits: number
  credits_this_week: number
  credits_this_month: number
  history: WalletHistory[]
}

export type Voucher = {
  id: number
  title: string
  description: string
  credits: number
  status: string
  category?: string | null
  rating: number
  availability: string
  redeemed_at?: string | null
  redeemed_by_user_id?: number | null
}
