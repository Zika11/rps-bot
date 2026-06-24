import { Routes, Route, Link } from 'react-router-dom'
import Game from './pages/Game'
import Leaderboard from './pages/Leaderboard'

function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <Link to="/" className="logo">🎮 RPS Game</Link>
        <div className="nav-links">
          <Link to="/">اللعبة</Link>
          <Link to="/leaderboard">المتصدرون</Link>
        </div>
      </nav>
      <main className="container">
        <Routes>
          <Route path="/" element={<Game />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
