import { useState, useEffect } from 'react'
import { getRoundStatus, submitVote } from '../api'

const CHAT_ID = -1001234567890  // استبدله بمعرف قناتك

function Game() {
  const [round, setRound] = useState(null)
  const [selectedMove, setSelectedMove] = useState(null)
  const [userId, setUserId] = useState(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    // محاكاة مستخدم عشوائي (يجب أن يكون لديك نظام تسجيل دخول حقيقي)
    setUserId(Math.floor(Math.random() * 1000000))
    const interval = setInterval(() => {
      getRoundStatus(CHAT_ID).then(data => setRound(data)).catch(console.error)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const handleVote = async () => {
    if (!selectedMove || !userId) return
    const result = await submitVote(CHAT_ID, userId, selectedMove)
    if (result.status === 'vote registered') {
      setMessage('تم تسجيل تصويتك!')
      setSelectedMove(null)
    } else {
      setMessage('فشل التصويت')
    }
  }

  return (
    <div>
      <h2>🎯 قناة RPS</h2>
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
