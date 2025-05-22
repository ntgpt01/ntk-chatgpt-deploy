from flask import Flask, render_template, request, redirect, url_for, session, send_file
from users import users
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # ✅ Đúng cú pháp mới
import os
import csv
from datetime import datetime
import os
from collections import defaultdict
import requests  # dùng để gửi tin nhắn lại cho Telegram


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
                        cost_vnd = round(total_tokens / 1000 * 250)
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            username,
                            prompt.replace("\n", "\\n"),
                            response_text.replace("\n", "\\n"),
                            total_tokens,
                            prompt_tokens,
                            completion_tokens,
                            cost_vnd  # thêm chi phí
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
    import json
# thêm vào cuối route

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

    return render_template("stats.html", stats=stats_data, chart_data=json.dumps(stats_data))
@app.route("/billing")
def billing():
    from collections import defaultdict

    billing_data = defaultdict(lambda: {"count": 0, "total_tokens": 0, "total_cost": 0})

    try:
        with open("usage_log.csv", newline="", encoding="utf-8") as f:
            reader = csv.reader(f) 
            headers = next(reader)
            for row in reader:
                if len(row) < 8:
                    continue  # bỏ dòng thiếu dữ liệu
                timestamp, username, *_ , total_tokens, _, _, cost_vnd = row
                month = timestamp[:7]  # YYYY-MM

                key = (username, month)
                billing_data[key]["count"] += 1
                billing_data[key]["total_tokens"] += int(total_tokens)
                billing_data[key]["total_cost"] += int(cost_vnd)
    except FileNotFoundError:
        pass

    # Chuyển thành danh sách để render dễ
    result = []
    for (user, month), data in billing_data.items():
        result.append({
            "username": user,
            "month": month,
            "count": data["count"],
            "tokens": data["total_tokens"],
            "cost": data["total_cost"]
        })

    # Sắp xếp theo tháng mới nhất
    result.sort(key=lambda x: (x["month"], x["username"]), reverse=True)

    return render_template("billing.html", billing=result)
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📩 Nhận từ Telegram:", data)  # THÊM DÒNG NÀY

    # Kiểm tra tin nhắn Telegram gửi đến
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Gọi GPT trả lời
        try:
            completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là trợ lý thân thiện."},
                {"role": "user", "content": prompt}  # hoặc `text` nếu dùng với Telegram
            ]
            )

            reply = completion.choices[0].message.content.strip()
        except Exception as e:
            reply = f"❌ Lỗi GPT: {e}"

        # Gửi lại kết quả về Telegram
        telegram_api_url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/sendMessage"
        requests.post(telegram_api_url, json={
            "chat_id": chat_id,
            "text": reply
        })

    return "ok"



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
