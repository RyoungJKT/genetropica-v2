import { createBrowserRouter, Navigate } from 'react-router-dom'
import App from './App'
import Overview from './pages/Overview'
import Explore from './pages/Explore'
import Binding from './pages/Binding'
import MD from './pages/MD'
import Conservation from './pages/Conservation'
import Methods from './pages/Methods'
import Validation from './pages/Validation'
import Diseases from './pages/Diseases'
import Escape from './pages/Escape'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'explore', element: <Explore /> },
      { path: 'binding', element: <Binding /> },
      { path: 'md', element: <MD /> },
      { path: 'conservation', element: <Conservation /> },
      { path: 'escape', element: <Escape /> },
      { path: 'methods', element: <Methods /> },
      { path: 'validation', element: <Validation /> },
      { path: 'diseases', element: <Diseases /> },
      // Unknown paths (including the removed /admet and /insights pages) go to the dashboard home.
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
], { basename: '/app' })
