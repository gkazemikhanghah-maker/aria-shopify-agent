export default function ProductCard({ product }) {
  const imageUrl = product.image_url || product.image || null
  const hasImage = imageUrl && !imageUrl.includes('placeholder')

  return (
    <div className="bg-aria-surface-light border border-aria-border rounded-xl p-3 flex items-center gap-3 hover:border-aria-primary/30 transition-colors animate-message-in cursor-pointer">
      <div className="w-14 h-14 rounded-lg overflow-hidden shrink-0 bg-aria-primary/10 flex items-center justify-center">
        {hasImage ? (
          <img
            src={imageUrl}
            alt={product.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-aria-primary/60">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z" strokeLinecap="round" strokeLinejoin="round" />
            <line x1="7" y1="7" x2="7.01" y2="7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="font-display font-medium text-aria-text text-xs leading-tight truncate">
          {product.title}
        </h4>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-aria-accent font-display font-semibold text-xs">
            {product.price_range}
          </span>
          {product.product_type && (
            <span className="text-aria-text-dim text-[10px] bg-aria-bg px-1.5 py-0.5 rounded-full">
              {product.product_type}
            </span>
          )}
        </div>
      </div>

      <div className="shrink-0 text-aria-text-dim">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>
    </div>
  )
}
