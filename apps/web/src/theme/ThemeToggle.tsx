import { useTheme } from './ThemeContext'

const LABELS = { light: 'Light', dark: 'Dark', system: 'System' } as const

export function ThemeToggle() {
  const { preference, cycle } = useTheme()
  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${LABELS[preference]}. Activate to change.`}
      className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-sm text-text hover:border-accent focus-visible:outline-2 focus-visible:outline-accent"
    >
      Theme: {LABELS[preference]}
    </button>
  )
}
