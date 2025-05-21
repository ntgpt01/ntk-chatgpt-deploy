from flask import Flask, render_template, request, redirect, url_for, session
from users import users
import openai
import csv
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "supersecret"  # Bắt buộc để dùng session

# Dùng biến môi trường thay vì hardcode API key
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
            completion = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là trợ lý thân thiện."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = completion.choices[0].message.content.strip()

            # Lấy token usage
            usage = completion.usage
            total_tokens = usage.total_tokens
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens

            # Ghi log ra CSV
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

    return render_template("chat.html", username=username, prompt=prompt, response=response_text)


@app.route("/usage")
def usage():
    if "username" not in session:
        return redirect(url_for("login"))

    rows = []
    try:
        with open("usage_log.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)  # Bỏ dòng tiêu đề

            for row in reader:
                # Bỏ qua dòng rỗng hoặc dòng không đủ 7 cột dữ liệu
                if len(row) != 7:
                    continue
                rows.append(row)
    except FileNotFoundError:
        rows = []

    return render_template("usage.html", rows=rows)

from flask import send_file

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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
