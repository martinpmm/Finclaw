import { useCallback, useEffect, useRef, useState } from 'react'
import { ChatSocket, WSMessage } from '../api/websocket'

export type Message = {
  role: 'user' | 'assistant'
  content: string
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const socketRef = useRef<ChatSocket | null>(null)
  const pendingRef = useRef('')

  useEffect(() => {
    const socket = new ChatSocket()
    socketRef.current = socket

    const unsub = socket.onMessage((msg: WSMessage) => {
      if (msg.type === 'connected') {
        setIsConnected(true)
        return
      }

      if (msg.type === 'progress') {
        // Accumulate streaming progress into the last assistant message
        pendingRef.current += msg.content || ''
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { role: 'assistant', content: pendingRef.current }]
          }
          return [...prev, { role: 'assistant', content: pendingRef.current }]
        })
        return
      }

      if (msg.type === 'message') {
        // Final message — replace any accumulated progress
        pendingRef.current = ''
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant') {
            return [...prev.slice(0, -1), { role: 'assistant', content: msg.content || '' }]
          }
          return [...prev, { role: 'assistant', content: msg.content || '' }]
        })
        setIsLoading(false)
      }
    })

    socket.connect()

    return () => {
      unsub()
      socket.disconnect()
    }
  }, [])

  const sendMessage = useCallback((content: string) => {
    if (!content.trim()) return

    setMessages((prev) => [...prev, { role: 'user', content }])
    setIsLoading(true)
    pendingRef.current = ''
    socketRef.current?.send(content)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, sendMessage, clearMessages, isConnected, isLoading }
}
