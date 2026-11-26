export function RadarMark() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      role="img"
      aria-label="Effort vs Result Radar"
      className="size-6 shrink-0"
    >
      <circle cx="12" cy="12" r="9" stroke="#E8B849" strokeWidth="1.5" />
      <path d="M12 4 A8 8 0 0 1 20 12" stroke="#E8B849" strokeWidth="1.5" />
      <path d="M12 0 A12 12 0 0 1 24 12" stroke="#E8B849" strokeWidth="1.5" />
    </svg>
  )
}
