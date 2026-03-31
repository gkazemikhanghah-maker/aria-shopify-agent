export default function MessageBubble({ role, content }) {
  const isUser = role === 'user'

  return (
    <div className={`flex items-end gap-2 animate-message-in ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-aria-primary/20 flex items-center justify-center shrink-0">
          <span className="text-aria-primary font-display font-bold text-xs">A</span>
        </div>
      )}

      {/* Bubble */}
      <div
        className={`
          max-w-[75%] px-3.5 py-2.5 text-sm leading-relaxed
          ${isUser
            ? 'bg-aria-user-bubble text-white rounded-2xl rounded-br-md'
            : 'bg-aria-bot-bubble text-aria-text rounded-2xl rounded-bl-md border border-aria-border'
          }
        `}
      >
        {content}
      </div>
    </div>
  )
}