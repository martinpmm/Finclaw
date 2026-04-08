import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'

export type Document = {
  title: string
  source_type: string
  date: string
  notes: string
  notes_preview: string
}

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<{ documents: Document[] }>('/api/documents')
      setDocuments(data.documents)
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [])

  const uploadFile = useCallback(async (file: File) => {
    const result = await api.upload<{ filename: string; message: string }>(
      '/api/documents/upload',
      file,
    )
    await fetchDocuments()
    return result
  }, [fetchDocuments])

  const deleteDocument = useCallback(async (title: string) => {
    await api.delete(`/api/documents/${encodeURIComponent(title)}`)
    await fetchDocuments()
  }, [fetchDocuments])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  return { documents, loading, uploadFile, deleteDocument, refresh: fetchDocuments }
}
