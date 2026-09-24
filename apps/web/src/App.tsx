import { ThemeToggle } from './theme/ThemeToggle'

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="flex items-center justify-between border-b border-border bg-surface px-6 py-4">
        <h1 className="text-lg font-semibold">DDQ Portfolio Dashboard</h1>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-muted">Portfolio risk analytics: Data Driven Quant.</p>
      </main>
    </div>
  )
}
