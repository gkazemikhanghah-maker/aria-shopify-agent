export default function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 animate-message-in">
      <div className="w-7 h-7 rounded-full bg-aria-primary/20 flex items-center justify-center shrink-0">
        <span className="text-aria-primary font-display font-bold text-xs">A</span>
      </div>
      <div className="bg-aria-bot-bubble border border-aria-border rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-aria-text-dim typing-dot" />
          <div className="w-1.5 h-1.5 rounded-full bg-aria-text-dim typing-dot" />
          <div className="w-1.5 h-1.5 rounded-full bg-aria-text-dim typing-dot" />
        </div>
      </div>
    </div>
  )
}