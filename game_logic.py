import random

# اختيارات اللعبة
CHOICES = ["rock", "paper", "scissors"]

# تحديد الفائز
def get_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return "draw"

    if (
        (user_choice == "rock" and bot_choice == "scissors") or
        (user_choice == "paper" and bot_choice == "rock") or
        (user_choice == "scissors" and bot_choice == "paper")
    ):
        return "win"

    return "lose"


# اختيار عشوائي للبوت
def get_bot_choice():
    return random.choice(CHOICES)


# --- 🏆 نظام الإنجازات ---

def check_achievements(user_data):
    achievements = []

    wins = user_data.get("wins", 0)
    games = user_data.get("games", 0)

    if wins >= 1:
        achievements.append("🎉 أول فوز!")
    if wins >= 5:
        achievements.append("🔥 5 انتصارات!")
    if wins >= 10:
        achievements.append("💪 10 انتصارات!")
    if wins >= 25:
        achievements.append("👑 أسطورة!")

    if games >= 10:
        achievements.append("🎮 لعبت 10 جولات!")
    if games >= 50:
        achievements.append("🧠 محترف RPS!")

    return achievements
