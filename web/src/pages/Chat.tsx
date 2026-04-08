import ChatPanel from '../components/ChatPanel'
import { useChat } from '../hooks/useChat'

export default function Chat() {
  const { messages, sendMessage, isConnected, isLoading } = useChat()

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Chat with Finclaw</h1>
        <p className="text-sm text-gray-500">
          Ask about companies, markets, add to watchlist, or analyze documents
        </p>
      </div>

      <ChatPanel
        messages={messages}
        onSend={sendMessage}
        isLoading={isLoading}
        isConnected={isConnected}
        className="flex-1"
      />
    </div>
  )
}
