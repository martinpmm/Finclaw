import { useCallback, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { useDocuments, Document } from '../hooks/useDocuments'

export default function Documents() {
  const { documents, loading, uploadFile, deleteDocument } = useDocuments()
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    setUploadMessage('')
    try {
      const result = await uploadFile(file)
      setUploadMessage(result.message)
    } catch {
      setUploadMessage('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [uploadFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleUpload(file)
  }, [handleUpload])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
    e.target.value = ''
  }, [handleUpload])

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-sm text-gray-500 mt-1">Upload and manage financial documents for AI analysis</p>
      </div>

      {/* Upload area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-8 text-center mb-6 transition-colors ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-white hover:border-gray-400'
        }`}
      >
        <svg className="w-10 h-10 mx-auto text-gray-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-gray-600 text-sm mb-2">
          {uploading ? 'Uploading...' : 'Drag & drop a file here, or click to browse'}
        </p>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          Choose File
        </button>
        <input ref={fileRef} type="file" className="hidden" accept=".pdf,.txt,.csv,.md" onChange={handleFileChange} />
      </div>

      {uploadMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-6 text-sm text-green-800">
          {uploadMessage}
        </div>
      )}

      {/* Document list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />)}
        </div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">No documents yet</p>
          <p className="text-gray-400 text-sm mt-1">Upload documents or use chat to ingest SEC filings, earnings calls, etc.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc: Document) => (
            <div key={doc.title} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div
                onClick={() => setExpanded(expanded === doc.title ? null : doc.title)}
                className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-gray-50"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{doc.title}</p>
                  <div className="flex items-center gap-3 mt-1">
                    {doc.source_type && (
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{doc.source_type}</span>
                    )}
                    {doc.date && <span className="text-xs text-gray-400">{doc.date}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteDocument(doc.title) }}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                  <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded === doc.title ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>

              {expanded === doc.title && (
                <div className="border-t border-gray-100 px-5 py-4 bg-gray-50">
                  <div className="prose text-sm text-gray-700">
                    <Markdown>{doc.notes || '_No notes extracted._'}</Markdown>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
