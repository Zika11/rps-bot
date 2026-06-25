# core/tournament_manager.py
import json
import db

def get_tournament(tour_id):
    return db.get_tournament(tour_id)

def update_tournament(tour_id, **kwargs):
    db.update_tournament(tour_id, **kwargs)

def get_bracket(tour_id):
    tour = db.get_tournament(tour_id)
    if not tour:
        return None
    return json.loads(tour.get("bracket", "{}"))

def save_bracket(tour_id, bracket):
    db.update_tournament(tour_id, bracket=json.dumps(bracket))

def get_match_data(tour_id):
    tour = db.get_tournament(tour_id)
    if not tour:
        return {}
    return json.loads(tour.get("match_data", "{}"))

def save_match_data(tour_id, match_data):
    db.update_tournament(tour_id, match_data=json.dumps(match_data))

def advance_round(tour_id, current_round, bracket):
    """تقدم البطولة للدور التالي بناءً على الفائزين"""
    round_key = f"round{current_round}"
    matches = bracket.get(round_key, [])
    winners = [m["winner"] for m in matches if m.get("winner") is not None]

    if current_round == 1 and len(winners) == 4:
        bracket["round2"] = [
            {"p1": winners[0], "p2": winners[1]},
            {"p1": winners[2], "p2": winners[3]}
        ]
        return 2, bracket
    elif current_round == 2 and len(winners) == 2:
        bracket["final"] = [{"p1": winners[0], "p2": winners[1]}]
        return 3, bracket
    elif current_round == 3 and len(winners) == 1:
        return "finished", bracket
    return current_round, bracket
