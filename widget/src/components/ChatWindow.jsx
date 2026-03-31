          // Fall back to REST API
          console.log('Falling back to REST API')
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

  // REST API fallback
  const sendViaRest = async (text) => {
    try {
      const resp = await fetch(`${API_BASE}/chat`, {
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
          content: "Sorry, I'm having trouble connecting. Please try again!",
          products: [],
        },
      ])
    }
  }

  const sendMessage = () => {
    const text = input.trim()
    if (!text) return

    // Add user message
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

  // Quick suggestion chips
  const suggestions = [
    "What's popular right now?",
    "Show me winter jackets",
    "Something under $50",
  ]

  const handleSuggestion = (text) => {
    setInput(text)
    setTimeout(() => {
      setInput('')
      setMessages((prev) => [...prev, { role: 'user', content: text, products: [] }])
      setIsTyping(true)

      if (useRest || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        sendViaRest(text)
      } else {
        wsRef.current.send(JSON.stringify({ message: text }))
      }
    }, 100)
  }

  return (
    <div className="w-[380px] h-[560px] bg-aria-surface rounded-2xl border border-aria-border shadow-2xl shadow-black/40 flex flex-col overflow-hidden font-body">
      
      {/* Header */}
      <div className="px-5 py-4 bg-gradient-to-r from-aria-primary/20 to-aria-accent/10 border-b border-aria-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-aria-primary flex items-center justify-center text-white font-display font-bold text-sm">
            A
          </div>
          <div>
            <h2 className="font-display font-semibold text-aria-text text-sm leading-tight">Aria</h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span className="text-xs text-aria-text-dim">
                {isConnected ? 'Online' : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-aria-text-dim hover:text-aria-text transition-colors cursor-pointer"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 aria-scrollbar">
        {messages.map((msg, i) => (
          <div key={i}>
            <MessageBubble
              role={msg.role}
              content={msg.content}
            />
            {msg.products && msg.products.length > 0 && (
              <div className="mt-2 ml-11 space-y-2">
                {msg.products.slice(0, 2).map((product, j) => (
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

      {/* Input */}
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