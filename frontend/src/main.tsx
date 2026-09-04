import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './stores/theme'
import { AuthProvider } from './stores/auth'
import { DemoModeProvider } from './stores/demoMode'
import { PortfolioProvider } from './stores/portfolio'
import { registerSW } from './pwa'

registerSW()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>
              <DemoModeProvider>
                <PortfolioProvider>
                  <App />
                </PortfolioProvider>
              </DemoModeProvider>
            </AuthProvider>
          </ToastProvider>
        </ThemeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
