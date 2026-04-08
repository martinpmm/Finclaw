import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Markdown from 'react-markdown'
import { useCompany } from '../hooks/useCompanies'
import { useChat } from '../hooks/useChat'
import ChatPanel from '../components/ChatPanel'

const tabs = ['Overview', 'Notes', 'Analysis'] as const
type Tab = typeof tabs[number]

export default function CompanyDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const { company, loading } = useCompany(symbol || '')
  const chat = useChat()
  const [activeTab, setActiveTab] = useState<Tab>('Overview')

  if (loading) {
    return (
      <div className="p-6">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-4" />
        <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    )
  }

  if (!company) {
    return (
      <div className="p-6 text-center py-16">
        <p className="text-gray-500 text-lg">Company not found</p>
        <Link to="/" className="text-blue-600 text-sm mt-2 inline-block hover:underline">Back to companies</Link>
      </div>
    )
  }

  const ratingColor: Record<string, string> = {
    Bullish: 'bg-green-100 text-green-800',
    Neutral: 'bg-yellow-100 text-yellow-800',
    Bearish: 'bg-red-100 text-red-800',
  }

  return (
    <div className="h-full flex">
      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-4xl">
          {/* Header */}
          <div className="flex items-center gap-3 mb-1">
            <Link to="/" className="text-gray-400 hover:text-gray-600">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">{company.symbol}</h1>
            {company.price && <span className="text-lg text-gray-600">{company.price}</span>}
            {company.rating && (
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${ratingColor[company.rating] || 'bg-gray-100'}`}>
                {company.rating}
              </span>
            )}
            {company.conviction && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                {company.conviction} conviction
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400 ml-8 mb-6">Added {company.added || 'N/A'}</p>

          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="flex gap-6">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          {activeTab === 'Overview' && (
            <div className="space-y-6">
              <section className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-900 mb-2">Investment Thesis</h3>
                <div className="prose text-sm text-gray-700">
                  <Markdown>{company.thesis || '_No thesis provided yet._'}</Markdown>
                </div>
              </section>

              <section className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-900 mb-2">Agent Opinion</h3>
                <div className="prose text-sm text-gray-700">
                  <Markdown>{company.opinion || '_No opinion formed yet._'}</Markdown>
                </div>
              </section>
            </div>
          )}

          {activeTab === 'Notes' && (
            <div className="space-y-3">
              {company.notes.length > 0 ? (
                company.notes.map((note, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 px-5 py-3">
                    <p className="text-sm text-gray-700">{note}</p>
                  </div>
                ))
              ) : (
                <p className="text-gray-400 text-sm">No notes yet.</p>
              )}
            </div>
          )}

          {activeTab === 'Analysis' && (
            <div className="space-y-3">
              {company.analyses && company.analyses.length > 0 ? (
                company.analyses.map((a, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-medium text-gray-500 uppercase">{String(a.analysis_type || '')}</span>
                      <span className="text-xs text-gray-400">{String(a.date || '')}</span>
                      {typeof a.rating === 'string' && a.rating && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ratingColor[a.rating] || 'bg-gray-100'}`}>
                          {a.rating}
                        </span>
                      )}
                    </div>
                    <div className="prose text-sm text-gray-700">
                      <Markdown>{String(a.content || '')}</Markdown>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-400 text-sm">No analyses stored yet. Ask Finclaw to analyze this company.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chat sidebar */}
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-3 border-b border-gray-200">
          <p className="text-sm font-medium text-gray-700">Ask about {company.symbol}</p>
        </div>
        <ChatPanel
          messages={chat.messages}
          onSend={chat.sendMessage}
          isLoading={chat.isLoading}
          isConnected={chat.isConnected}
          placeholder={`Ask about ${company.symbol}...`}
          className="flex-1"
        />
      </div>
    </div>
  )
}
