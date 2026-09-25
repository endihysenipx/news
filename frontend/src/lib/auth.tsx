"use client"

import * as React from "react"
import type { User } from "./types"

type AuthContextValue = {
  user: User | null
  loading: boolean
  apiFetch: (path: string, init?: RequestInit) => Promise<Response>
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null)
  const [loading, setLoading] = React.useState(true)

  const apiFetch = React.useCallback(async (path: string, init?: RequestInit) => {
    const response = await fetch(`/api${path}`, { ...init, credentials: "same-origin", cache: "no-store" })
    if (response.status === 401) setUser(null)
    return response
  }, [])

  React.useEffect(() => {
    let active = true
    fetch("/api/auth/me", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => response.ok ? await response.json() as User : null)
      .then((result) => { if (active) setUser(result) })
      .catch(() => { if (active) setUser(null) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const login = React.useCallback(async (email: string, password: string) => {
    const response = await fetch("/api/auth/login", {
      method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok) throw new Error(typeof payload?.detail === "string" ? payload.detail : "Sign in failed")
    setUser(payload as User)
  }, [])

  const logout = React.useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" })
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, loading, apiFetch, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used within AuthProvider")
  return context
}
