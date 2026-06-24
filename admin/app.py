from flask import Flask, render_template, redirect, url_for, request, session
from functools import wraps
import sqlite3, os, json
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = os.urandom(24)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "rps2024"  # غيرها

DB = os.path.join(os.path.dirname(__file__), "..", "rps_bot.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="بيانات خاطئة")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# ---------- Dashboard ----------
@app.route("/")
@login_required
def dashboard():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_games = conn.execute("SELECT COUNT(*) FROM active_games").fetchone()[0]
    total_clans = conn.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
    # بيانات الرانكات
    top_ratings = conn.execute("""
        SELECT u.first_name, r.rating FROM ratings r
        JOIN users u ON r.user_id = u.user_id
        ORDER BY r.rating DESC LIMIT 5
    """).fetchall()
    # نشاط يومي (آخر 7 أيام)
    daily_activity = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        count = conn.execute("SELECT COUNT(*) FROM users WHERE date(last_login) = ?", (d,)).fetchone()[0]
        daily_activity.append({"date": d, "count": count})
    conn.close()
    return render_template("dashboard.html",
                           total_users=total_users,
                           total_games=total_games,
                           total_clans=total_clans,
                           top_ratings=top_ratings,
                           daily_activity=daily_activity)

# ---------- Users ----------
@app.route("/users")
@login_required
def users():
    search = request.args.get("search", "")
    conn = get_db()
    if search:
        rows = conn.execute("SELECT * FROM users WHERE user_id LIKE ? OR first_name LIKE ?",
                            (f"%{search}%", f"%{search}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users ORDER BY points DESC LIMIT 50").fetchall()
    conn.close()
    return render_template("users.html", users=rows, search=search)

# ---------- Broadcast ----------
@app.route("/broadcast", methods=["GET", "POST"])
@login_required
def broadcast():
    if request.method == "POST":
        message = request.form["message"]
        conn = get_db()
        users = conn.execute("SELECT user_id FROM users").fetchall()
        # هنا ممكن تبعته عبر البوت لو البوت شغال، أو تخزنه
        # هنحاكي إرسال وهمي
        conn.close()
        return render_template("broadcast.html", success=f"تم الإرسال إلى {len(users)} مستخدم")
    return render_template("broadcast.html")

# ---------- Clans ----------
@app.route("/clans")
@login_required
def clans():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clans ORDER BY points DESC").fetchall()
    conn.close()
    return render_template("clans.html", clans=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
