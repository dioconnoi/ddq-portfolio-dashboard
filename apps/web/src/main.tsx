import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/index.css'
import { ThemeProvider } from './theme/ThemeProvider'

const root = document.getElementById('root')
if (root === null) throw new Error('Missing #root element')

// The status hook owns the retry count; the delay between attempts lives here.
const queryClient = new QueryClient({
  defaultOptions: { queries: { retryDelay: 1500 } },
})

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
