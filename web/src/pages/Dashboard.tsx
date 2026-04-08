import { useNavigate } from 'react-router-dom'
import { useCompanies } from '../hooks/useCompanies'

const ratingColor: Record<string, string> = {
  Bullish: 'bg-green-100 text-green-800',
  Neutral: 'bg-yellow-100 text-yellow-800',
  Bearish: 'bg-red-100 text-red-800',
}

const convictionColor: Record<string, string> = {
  High: 'bg-blue-100 text-blue-800',
  Medium: 'bg-gray-100 text-gray-700',
  Low: 'bg-gray-50 text-gray-500',
}

export default function Dashboard() {
  const { companies, loading } = useCompanies()
  const navigate = useNavigate()

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
          <p className="text-sm text-gray-500 mt-1">Your tracked companies and investment theses</p>
        </div>
        <button
          onClick={() => navigate('/chat')}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + Add via Chat
        </button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : companies.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <p className="text-gray-500 text-lg">No companies tracked yet</p>
          <p className="text-gray-400 text-sm mt-1">Chat with Finclaw to add companies to your watchlist</p>
          <button
            onClick={() => navigate('/chat')}
            className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Start a Chat
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Symbol</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Price</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Rating</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Conviction</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Added</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Thesis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {companies.map((c) => (
                <tr
                  key={c.symbol}
                  onClick={() => navigate(`/company/${c.symbol}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-semibold text-gray-900">{c.symbol}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.price || '—'}</td>
                  <td className="px-4 py-3">
                    {c.rating ? (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${ratingColor[c.rating] || 'bg-gray-100 text-gray-600'}`}>
                        {c.rating}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {c.conviction ? (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${convictionColor[c.conviction] || 'bg-gray-100 text-gray-600'}`}>
                        {c.conviction}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.added || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                    {c.thesis && !c.thesis.startsWith('_') ? c.thesis : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
