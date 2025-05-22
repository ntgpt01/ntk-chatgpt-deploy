from flask import Flask, render_template, request, redirect, url_for, session, send_file
from users import users
import openai
import csv
from datetime import datetime
import os
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "supersecret"
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username and password:
            if username in users and users[username]["password"] == password:
                session["username"] = username
                return redirect(url_for("chat"))
            else:
                error = "Tên đăng nhập hoặc mật khẩu không đúng."
        else:
            error = "Vui lòng nhập đầy đủ thông tin."
    return render_template("login.html", error=error)


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    response_text = ""
    prompt = ""

    if request.method == "POST":
        prompt = request.form["prompt"]
        if prompt:
            try:
                completion = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Bạn là trợ lý thân thiện."},
                        {"role": "user", "content": prompt}
                    ]
                )
                if completion.choices:
                    response_text = completion.choices[0].message.content.strip()
                    usage = completion.usage
                    total_tokens = usage.total_tokens
                    prompt_tokens = usage.prompt_tokens
                    completion_tokens = usage.completion_tokens

                    with open("usage_log.csv", "a", encoding="utf-8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            username,
                            prompt.replace("\n", "\\n"),
                            response_text.replace("\n", "\\n"),
                            total_tokens,
                            prompt_tokens,
                            completion_tokens
                        ])
                else:
                    response_text = "❌ GPT không phản hồi."
            except Exception as e:
                response_text = f"❌ Lỗi khi gọi GPT: {e}"

    return render_template("chat.html", username=username, prompt=prompt, response=response_text)


@app.route("/usage")
def usage():
    if "username" not in session:
        return redirect(url_for("login"))

    rows = []
    try:
        with open("usage_log.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                if len(row) == 7:
                    rows.append(row)
    except FileNotFoundError:
        rows = []

    return render_template("usage.html", rows=rows)


@app.route("/download")
def download_log():
    if "username" not in session:
        return redirect(url_for("login"))

    return send_file(
        "usage_log.csv",
        mimetype="text/csv",
        as_attachment=True,
        download_name="usage_log.csv"
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/stats")
def stats():
    if "username" not in session:
        return redirect(url_for("login"))

    stats_data = defaultdict(lambda: {"count": 0, "total_tokens": 0})
    try:
        with open("usage_log.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) == 7:
                    user = row[1]
                    total_tokens = int(row[4]) if row[4].isdigit() else 0
                    stats_data[user]["count"] += 1
                    stats_data[user]["total_tokens"] += total_tokens
    except FileNotFoundError:
        pass

    # Thêm chi phí ước tính (250 VNĐ / 1000 tokens)
    for user in stats_data:
        tks = stats_data[user]["total_tokens"]
        stats_data[user]["cost"] = round((tks / 1000) * 250)

    return render_template("stats.html", stats=stats_data)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
