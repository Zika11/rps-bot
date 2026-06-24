import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getLeaderboard } from '../api'
import TelegramLoginButton from '../components/TelegramLoginButton'

const BOT_NAME = 'YOUR_BOT_USERNAME' // ← استبدله باسم مستخدم البوت

function Leaderboard() {
  const [searchParams] = useSearchParams()
  const chatId = searchParams.get('chat') || '-1001234567890'

  const [players, setPlayers] = useState([])
  const [user, setUser] = useState(null)

  useEffect(() => {
    const savedUser = localStorage.getItem('rps_user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  useEffect(() => {
    if (!user) return
    if (chatId) {
      getLeaderboard(chatId)
        .then(data => setPlayers(data))
        .catch(console.error)
    }
  }, [chatId, user])

  const handleTelegramAuth = (telegramUser) => {
    fetch(`${import.meta.env.VITE_API_URL}/auth/telegram`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(telegramUser)
    }).then(res => res.json()).then(data => {
      if (data.valid) {
        setUser(telegramUser)
        localStorage.setItem('rps_user', JSON.stringify(telegramUser))
      }
    }).catch(console.error)
  }

  if (!user) {
    return (
      <div className="auth-container">
        <h2>تسجيل الدخول للمشاهدة</h2>
        <TelegramLoginButton botName={BOT_NAME} onAuth={handleTelegramAuth} />
      </div>
    )
  }

  return (
    <div>
      <h2>🏆 المتصدرون</h2>
      <p>مرحبًا، {user.first_name}!</p>
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
