import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './lib/query'
import { RegisterProvider } from './state/register'
import { router } from './router'
import './styles/tokens.css'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RegisterProvider>
        <RouterProvider router={router} />
      </RegisterProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
