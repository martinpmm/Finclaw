import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type Company = {
  symbol: string
  added: string
  price: string
  thesis: string
  opinion: string
  rating: string
  conviction: string
  notes: string[]
  analyses?: Array<Record<string, unknown>>
  events?: Array<Record<string, unknown>>
}

export function useCompanies() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)

  const fetchCompanies = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ companies: Company[] }>('/api/companies')
      setCompanies(data.companies)
    } catch {
      setCompanies([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCompanies()
  }, [fetchCompanies])

  return { companies, loading, refresh: fetchCompanies }
}

export function useCompany(symbol: string) {
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    api.get<Company>(`/api/companies/${symbol}`)
      .then((data) => {
        if ('error' in data) setCompany(null)
        else setCompany(data)
      })
      .catch(() => setCompany(null))
      .finally(() => setLoading(false))
  }, [symbol])

  return { company, loading }
}
