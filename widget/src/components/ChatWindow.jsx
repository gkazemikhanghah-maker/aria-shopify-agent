import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import ProductCard from './ProductCard'
import TypingIndicator from './TypingIndicator'

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://aria-shopify-agent.onrender.com'

const WS_URL = window.location.hostname === 'localhost'
  ? 'ws://localhost:8000/ws/chat'
  : 'wss://aria-shopify-agent.onrender.com/ws/chat'

export default function ChatWindow({ onClose }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "hey! i'm Aria ✨ what are you looking for today?",
      products: [],
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [useRest, setUseRest] = useState(false)
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    let retryCount = 0
    const maxRetries = 3

    const connect = () => {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        setIsConnected(true)
        retryCount = 0
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setIsTyping(false)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.response,
            products: data.products || [],
          },
        ])
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (retryCount < maxRetries) {
          retryCount++
          setTimeout(connect, 3000)
        } else {
          setUseRest(true)
          setIsConnected(true)
        }
      }

      ws.onerror = () => {
        setIsConnected(false)
      }

      wsRef.current = ws
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const sendViaRest = async (text) => {
    try {
      const resp = await fetch(API_BASE + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await resp.json()
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          products: data.products || [],
        },
      ])
    } catch (err) {
      setIsTyping(false)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "sorry, having a connection issue — try again in a sec!",
          products: [],
        },
      ])
    }
  }

  const sendMessage = () => {
    const text = input.trim()
    if (!text) return

    setMessages((prev) => [...prev, { role: 'user', content: text, products: [] }])
    setInput('')
    setIsTyping(true)

    if (useRest || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      sendViaRest(text)
    } else {
      wsRef.current.send(JSON.stringify({ message: text }))
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const suggestions = [
    "What's trending right now?",
    "I need a skincare routine",
    "Something cozy for my room",
    "Best headphones under $150",
  ]

  const handleSuggestion = (text) => {
    setMessages((prev) => [...prev, { role: 'user', content: text, products: [] }])
    setIsTyping(true)

    if (useRest || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      sendViaRest(text)
    } else {
      wsRef.current.send(JSON.stringify({ message: text }))
    }
  }

  return (
    <div className="w-[380px] h-[560px] bg-aria-surface rounded-2xl border border-aria-border shadow-2xl shadow-black/40 flex flex-col overflow-hidden font-body">
      <div className="px-5 py-4 bg-gradient-to-r from-aria-primary/20 to-aria-accent/10 border-b border-aria-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-aria-primary flex items-center justify-center text-white font-display font-bold text-sm">
            A
          </div>
          <div>
            <h2 className="font-display font-semibold text-aria-text text-sm leading-tight">Aria</h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={'w-1.5 h-1.5 rounded-full ' + (isConnected ? 'bg-emerald-400' : 'bg-amber-400')} />
              <span className="text-xs text-aria-text-dim">
                {isConnected ? 'Online' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
        <button onClick={onClose} className="text-aria-text-dim hover:text-aria-text transition-colors cursor-pointer">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 aria-scrollbar">
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble role={msg.role} content={msg.content} />
            {msg.products && msg.products.length > 0 && (
              <div className="mt-2 ml-11 space-y-2">
                {msg.products.slice(0, 3).map((product, j) => (
                  <ProductCard key={j} product={product} />
                ))}
              </div>
            )}
          </div>
        ))}

        {isTyping && <TypingIndicator />}

        {messages.length === 1 && (
          <div className="flex flex-wrap gap-2 mt-2 ml-11">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSuggestion(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-aria-border text-aria-text-dim hover:text-aria-text hover:border-aria-primary/50 hover:bg-aria-primary/10 transition-all cursor-pointer"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="px-4 py-3 border-t border-aria-border bg-aria-surface shrink-0">
        <div className="flex items-center gap-2 bg-aria-surface-light rounded-xl px-4 py-2.5 border border-aria-border focus-within:border-aria-primary/50 transition-colors">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything..."
            className="flex-1 bg-transparent text-aria-text text-sm placeholder:text-aria-text-dim/50 outline-none font-body"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim()}
            className="text-aria-primary hover:text-aria-accent disabled:text-aria-text-dim/30 transition-colors cursor-pointer disabled:cursor-default"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
