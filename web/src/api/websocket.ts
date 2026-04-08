export type WSMessage = {
  type: 'connected' | 'message' | 'progress'
  content?: string
  client_id?: string
  is_tool_hint?: boolean
}

export type WSListener = (msg: WSMessage) => void

export class ChatSocket {
  private ws: WebSocket | null = null
  private listeners: WSListener[] = []
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    this.ws = new WebSocket(`${proto}://${location.host}/ws/chat`)

    this.ws.onmessage = (e) => {
      try {
        const msg: WSMessage = JSON.parse(e.data)
        this.listeners.forEach((fn) => fn(msg))
      } catch { /* ignore malformed */ }
    }

    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 2000)
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  send(content: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ content }))
    }
  }

  onMessage(fn: WSListener) {
    this.listeners.push(fn)
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn)
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}
