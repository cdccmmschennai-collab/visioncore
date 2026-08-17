interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  label?: string
}

export default function SearchInput({ value, onChange, placeholder, label = 'Search' }: Props) {
  return (
    <div className="search">
      <span className="search-glyph" aria-hidden="true">⌕</span>
      <input
        type="search"
        className="input search-input"
        value={value}
        placeholder={placeholder}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
      />
      {value && (
        <button
          type="button"
          className="search-clear"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          ×
        </button>
      )}
    </div>
  )
}
