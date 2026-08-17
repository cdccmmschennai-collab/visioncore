export default function Spinner({ size = 18, label }: { size?: number; label?: string }) {
  return (
    <span className="spinner-wrap">
      <span
        className="spinner"
        style={{ width: size, height: size, borderWidth: Math.max(2, size / 9) }}
        aria-hidden="true"
      />
      {label && <span className="muted">{label}</span>}
    </span>
  )
}
