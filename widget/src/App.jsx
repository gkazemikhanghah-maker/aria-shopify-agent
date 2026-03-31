import { useState } from 'react'
import ChatWindow from './components/ChatWindow'

// Floating Action Button + Chat Window
export default function App() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      {/* Demo page background */}
      <div className="fixed inset-0 bg-aria-bg" />

      {/* Demo store hint */}
      <div className="fixed top-8 left-1/2 -translate-x-1/2 z-10 text-center">
        <h1 className="font-display text-3xl font-bold text-aria-text tracking-tight">
          Aria Demo Store
        </h1>
        <p className="font-body text-aria-text-dim mt-2 text-sm">
          Click the chat bubble to talk to Aria ✨
        </p>
      </div>

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 animate-widget-open">
          <ChatWindow onClose={() => setIsOpen(false)} />
        </div>
      )}

      {/* Floating Action Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full
          flex items-center justify-center
          bg-aria-primary hover:bg-aria-primary-dark
          text-white shadow-lg shadow-aria-primary/30
          transition-all duration-300 cursor-pointer
          ${!isOpen ? 'animate-pulse-glow' : ''}
          hover:scale-105 active:scale-95
        `}
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
    </>
  )
}
