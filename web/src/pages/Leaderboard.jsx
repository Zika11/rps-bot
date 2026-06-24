import { useState, useEffect } from 'react'
import { getLeaderboard } from '../api'

const CHAT_ID = -1001234567890

function Leaderboard() {
  const [players, setPlayers] = useState([])

  useEffect(() => {
    getLeaderboard(CHAT_ID)
      .then(data => setPlayers(data))
      .catch(console.error)
  }, [])

  return (
    <div>
      <h2>🏆 المتصدرون</h2>
      <ul className="leaderboard">
        {players.map((p, i) => (
          <li key={i}>
            <span>{i+1}. {p.name}</span>
            <span>{p.points} نقطة</span>
          </li>
        ))}
        {players.length === 0 && <li>لا توجد بيانات بعد</li>}
      </ul>
    </div>
  )
}

export default Leaderboard
