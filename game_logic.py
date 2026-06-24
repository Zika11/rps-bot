import random

# الاختيارات
CHOICES = ["rock", "paper", "scissors"]

# تحديد الفائز
def determine_winner(player_choice, bot_choice):
    if player_choice == bot_choice:
        return "draw"
    elif (
        (player_choice == "rock" and bot_choice == "scissors") or
        (player_choice == "paper" and bot_choice == "rock") or
        (player_choice == "scissors" and bot_choice == "paper")
    ):
        return "win"
    else:
        return "lose"


# اختيار البوت
def get_bot_choice():
    return random.choice(CHOICES)


# تشغيل جولة كاملة
def play_round(player_choice):
    bot_choice = get_bot_choice()
    result = determine_winner(player_choice, bot_choice)

    return {
        "player_choice": player_choice,
        "bot_choice": bot_choice,
        "result": result
    }


# تحديث إحصائيات اللاعب
def update_stats(user_data, result):
    if "wins" not in user_data:
        user_data["wins"] = 0
    if "losses" not in user_data:
        user_data["losses"] = 0
    if "draws" not in user_data:
        user_data["draws"] = 0
    if "games" not in user_data:
        user_data["games"] = 0

    user_data["games"] += 1

    if result == "win":
        user_data["wins"] += 1
    elif result == "lose":
        user_data["losses"] += 1
    else:
        user_data["draws"] += 1

    return user_data


# 🏆 نظام الإنجازات (FIX للمشكلة)
def check_achievements(user_id, user_data=None):
    """
    فحص الإنجازات
    """
    achievements = []

    if not user_data:
        return achievements

    wins = user_data.get("wins", 0)
    games = user_data.get("games", 0)

    # أول فوز
    if wins >= 1:
        achievements.append("🏆 أول فوز!")

    # 10 انتصارات
    if wins >= 10:
        achievements.append("🔥 محترف!")

    # 50 لعبة
    if games >= 50:
        achievements.append("🎮 مدمن لعب!")

    return achievements
