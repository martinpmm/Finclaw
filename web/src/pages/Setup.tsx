import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

type Provider = {
  name: string
  display_name: string
  has_key: boolean
  masked_key: string
  is_gateway: boolean
}

type SetupStatus = {
  providers: Provider[]
  current_model: string
  active_provider: string
  channels: Record<string, { enabled: boolean; configured: boolean }>
  has_provider: boolean
}

const CHANNEL_INFO: Record<string, { label: string; tokenLabel: string; help: string }> = {
  telegram: { label: 'Telegram', tokenLabel: 'Bot Token', help: 'Get from @BotFather on Telegram' },
  slack: { label: 'Slack', tokenLabel: 'Bot Token', help: 'Get from Slack App settings (xoxb-...)' },
  whatsapp: { label: 'WhatsApp', tokenLabel: 'Bridge Token', help: 'Requires the WhatsApp bridge running' },
  discord: { label: 'Discord', tokenLabel: 'Bot Token', help: 'Get from Discord Developer Portal' },
}

export default function Setup() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<SetupStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [channelTokens, setChannelTokens] = useState<Record<string, string>>({})

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.get<SetupStatus>('/api/setup/status')
      setStatus(data)
      setModel(data.current_model)
      setSelectedProvider(data.active_provider !== 'none' ? data.active_provider : '')
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const saveProvider = async () => {
    if (!selectedProvider || !apiKey) return
    setSaving(true)
    setSaved(false)
    try {
      await api.post('/api/setup/provider', {
        name: selectedProvider,
        api_key: apiKey,
        model: model || undefined,
      })
      setSaved(true)
      setApiKey('')
      await fetchStatus()
    } catch {
      /* ignore */
    } finally {
      setSaving(false)
    }
  }

  const saveChannel = async (name: string) => {
    const token = channelTokens[name]
    if (!token) return
    try {
      await api.post(`/api/setup/channel/${name}`, {
        enabled: true,
        token,
      })
      setChannelTokens((prev) => ({ ...prev, [name]: '' }))
      await fetchStatus()
    } catch {
      /* ignore */
    }
  }

  if (loading) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse mb-6" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <div key={i} className="h-32 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  const mainProviders = status?.providers.filter((p) => !p.is_gateway) || []

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Setup</h1>
        <p className="text-sm text-gray-500 mt-1">Configure your AI provider and messaging channels</p>
      </div>

      {/* AI Provider */}
      <section className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">AI Provider</h2>
        <p className="text-sm text-gray-500 mb-4">
          {status?.has_provider
            ? `Active: ${status.active_provider} (${status.current_model})`
            : 'Configure an AI provider to get started'}
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select a provider...</option>
              {mainProviders.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.display_name || p.name} {p.has_key ? '(configured)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter API key..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. anthropic/claude-sonnet-4-5"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={saveProvider}
              disabled={!selectedProvider || !apiKey || saving}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : 'Save Provider'}
            </button>
            {saved && <span className="text-green-600 text-sm">Saved successfully!</span>}
          </div>
        </div>
      </section>

      {/* Channels */}
      <section className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Messaging Channels</h2>
        <p className="text-sm text-gray-500 mb-4">Connect messaging platforms to chat with Finclaw outside the web UI</p>

        <div className="space-y-4">
          {Object.entries(CHANNEL_INFO).map(([name, info]) => {
            const ch = status?.channels[name]
            return (
              <div key={name} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{info.label}</span>
                    {ch?.enabled && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Connected</span>
                    )}
                  </div>
                </div>
                {!ch?.enabled && (
                  <div className="flex gap-2 mt-2">
                    <input
                      type="password"
                      value={channelTokens[name] || ''}
                      onChange={(e) => setChannelTokens((prev) => ({ ...prev, [name]: e.target.value }))}
                      placeholder={info.tokenLabel}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    <button
                      onClick={() => saveChannel(name)}
                      disabled={!channelTokens[name]}
                      className="bg-gray-900 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
                    >
                      Connect
                    </button>
                  </div>
                )}
                <p className="text-xs text-gray-400 mt-2">{info.help}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Continue */}
      {status?.has_provider && (
        <div className="text-center">
          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 text-white px-8 py-3 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      )}
    </div>
  )
}
