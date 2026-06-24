import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getLeaderboard } from '../api'

function Leaderboard() {
  const [searchParams] = useSearchParams()
  const chatId = searchParams.get('chat') || '-1001234567890'

  const [players, setPlayers] = useState([])

  useEffect(() => {
    if (chatId) {
      getLeaderboard(chatId)
        .then(data => setPlayers(data))
        .catch(console.error)
    }
  }, [chatId])

  return (
    <div>
      <h2>🏆 المتصدرون</h2>
      <p>معرف القناة: <strong>{chatId}</strong></p>
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
