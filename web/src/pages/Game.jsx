import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getRoundStatus, submitVote } from '../api'
import TelegramLoginButton from '../components/TelegramLoginButton'

const BOT_NAME = 'YOUR_BOT_USERNAME' // ← استبدله باسم مستخدم البوت

function Game() {
  const [searchParams] = useSearchParams()
  const chatId = searchParams.get('chat') || '-1001234567890'

  const [round, setRound] = useState(null)
  const [selectedMove, setSelectedMove] = useState(null)
  const [user, setUser] = useState(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const savedUser = localStorage.getItem('rps_user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  useEffect(() => {
    if (!user) return
    const interval = setInterval(() => {
      if (chatId) {
        getRoundStatus(chatId).then(data => setRound(data)).catch(console.error)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [chatId, user])

  const handleVote = async () => {
    if (!selectedMove || !user || !chatId) return
    const result = await submitVote(chatId, user.id, selectedMove)
    if (result.status === 'vote registered') {
      setMessage('تم تسجيل تصويتك!')
      setSelectedMove(null)
    } else {
      setMessage('فشل التصويت')
    }
  }

  const handleTelegramAuth = (telegramUser) => {
    fetch(`${import.meta.env.VITE_API_URL}/auth/telegram`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(telegramUser)
    }).then(res => res.json()).then(data => {
      if (data.valid) {
        setUser(telegramUser)
        localStorage.setItem('rps_user', JSON.stringify(telegramUser))
      } else {
        setMessage('فشل التحقق من الحساب')
      }
    }).catch(() => setMessage('خطأ في الاتصال بالخادم'))
  }

  if (!user) {
    return (
      <div className="auth-container">
        <h2>تسجيل الدخول للمشاركة</h2>
        <TelegramLoginButton botName={BOT_NAME} onAuth={handleTelegramAuth} />
      </div>
    )
  }

  return (
    <div>
      <h2>🎯 قناة RPS</h2>
      <p>مرحبًا، {user.first_name}!</p>
      <p>معرف القناة: <strong>{chatId}</strong></p>
      <div className="card">
        <p>حالة الجولة: {round?.status === 'ACTIVE' ? 'مفتوحة' : round?.status || 'لا توجد جولة نشطة'}</p>
        {round && <p>عدد المصوتين: {round.players_count ?? 0}</p>}
      </div>
      <div className="moves">
        {['rock', 'paper', 'scissors'].map(move => (
          <button
            key={move}
            className={`move-btn ${selectedMove === move ? 'selected' : ''}`}
            onClick={() => setSelectedMove(move)}
            disabled={!round || round.status !== 'ACTIVE'}
          >
            {move === 'rock' ? '👊' : move === 'paper' ? '✋' : '✌️'}
          </button>
        ))}
      </div>
      <button className="btn btn-primary" onClick={handleVote} disabled={!selectedMove}>
        تأكيد التصويت
      </button>
      {message && <p style={{ marginTop: '1rem' }}>{message}</p>}
    </div>
  )
}

export default Game
