import random


# =========================
# 🎮 GAME STATE CLASS
# =========================
class GameState:
    def __init__(self):
        self.solo_games = {}

    def start_solo_game(self, user_id):
        game_id = random.randint(1000, 9999)

        self.solo_games[game_id] = {
            "user_id": user_id
        }

        return game_id

    def play_solo_round(self, game_id, player_choice):
        if game_id not in self.solo_games:
            return None

        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)

        result = self.get_result(player_choice, bot_choice)

        return {
            "player": player_choice,
            "bot": bot_choice,
            "result": result
        }

    def finish_solo_game(self, game_id):
        if game_id in self.solo_games:
            del self.solo_games[game_id]

    def get_result(self, player, bot):
        if player == bot:
            return "تعادل 🤝"

        if (
            (player == "rock" and bot == "scissors") or
            (player == "paper" and bot == "rock") or
            (player == "scissors" and bot == "paper")
        ):
            return "فوز 🎉"

        return "خسارة 😢"


# =========================
# 🔥 IMPORTANT (ده اللي كان ناقص)
# =========================
state = GameState()
