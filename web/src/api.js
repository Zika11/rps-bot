const API_BASE = import.meta.env.VITE_API_URL || 'https://rps-bot-production-50cc.up.railway.app'

export async function getRoundStatus(chatId) {
  const res = await fetch(`${API_BASE}/round/${chatId}`)
  return res.json()
}

export async function submitVote(chatId, userId, move) {
  const res = await fetch(`${API_BASE}/vote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, user_id: userId, move })
  })
  return res.json()
}

export async function getLeaderboard(chatId) {
  const res = await fetch(`${API_BASE}/leaderboard/${chatId}`)
  return res.json()
}
