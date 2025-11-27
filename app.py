import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from scheduler import SchedulerManager
from supabase_client import SupabaseStorage
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "yal_secret_key_2025")

print("[FIX32] app.py loaded")

# Initialize Supabase
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_KEY")

storage = SupabaseStorage(SUPA_URL, SUPA_KEY)

# Initialize scheduler
scheduler = SchedulerManager(storage)
scheduler.start()

@app.route("/")
def home():
    files = storage.list_files()
    return render_template("home.html", files=files)

@app.route("/storage", methods=["GET","POST"])
def storage_page():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file provided", "danger")
            return redirect(url_for("storage_page"))

        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)

        if storage.upload_file(temp_path, file.filename):
            flash("Upload successful", "success")
        else:
            flash("Upload failed", "danger")

        try: os.remove(temp_path)
        except: pass

        return redirect(url_for("storage_page"))

    files = storage.list_files()
    return render_template("storage.html", files=files)

@app.route("/schedule", methods=["POST"])
def schedule():
    title = request.form.get("title")
    file_path = request.form.get("file_path")
    dt_iso = request.form.get("datetime")
    duration = int(request.form.get("duration") or 30)
    stream_key = request.form.get("stream_key")
    rtmp = request.form.get("rtmp") or "rtmp://a.rtmp.youtube.com/live2"

    try:
        dt = datetime.fromisoformat(dt_iso)
    except:
        flash("Invalid datetime format", "danger")
        return redirect(url_for("home"))

    job_id = scheduler.schedule_stream(title, file_path, dt, duration, rtmp, stream_key)
    flash("Live scheduled successfully!", "success")
    return redirect(url_for("home"))

@app.route("/healthz")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
