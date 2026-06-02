import { createBrowserRouter } from 'react-router-dom'
import App from './App'
import Overview from './pages/Overview'
import Explore from './pages/Explore'
import Binding from './pages/Binding'
import MD from './pages/MD'
import Admet from './pages/Admet'
import Conservation from './pages/Conservation'
import Insights from './pages/Insights'
import Methods from './pages/Methods'
import Validation from './pages/Validation'
import Diseases from './pages/Diseases'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Overview /> },
      { path: 'explore', element: <Explore /> },
      { path: 'binding', element: <Binding /> },
      { path: 'md', element: <MD /> },
      { path: 'admet', element: <Admet /> },
      { path: 'conservation', element: <Conservation /> },
      { path: 'insights', element: <Insights /> },
      { path: 'methods', element: <Methods /> },
      { path: 'validation', element: <Validation /> },
      { path: 'diseases', element: <Diseases /> },
    ],
  },
])
