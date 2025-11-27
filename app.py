print('[DEBUG] APP.PY LOADED SUCCESSFULLY')
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from auth import auth_blueprint, init_db
from scheduler import scheduler
from config import SECRET_KEY
from supabase import list_files, get_public_url, upload_file_to_supabase
import os

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    files = list_files() or []
    file_list = []
    for f in files:
        name = f.get("name")
        url = get_public_url(name)
        file_list.append({"name": name, "url": url})

    return render_template("home.html", files=file_list)

@app.route("/scheduled")
def scheduled():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    from supabase import get_schedules
    schedules = get_schedules()
    return render_template("scheduled.html", schedules=schedules)

@app.route("/storage")
def storage():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    files = list_files() or []
    file_list = []
    for f in files:
        file_list.append({
            "name": f.get("name"),
            "url": get_public_url(f.get("name")),
            "size": (f.get("metadata") or {}).get("size", 0)
        })

    return render_template("storage.html", files=file_list)

@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    from supabase import get_history
    history_list = get_history()
    return render_template("history.html", history=history_list)

@app.route("/reset_password")
def reset_password():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    file = request.files.get("file")
    if not file:
        flash("Tidak ada file yang dipilih", "danger")
        return redirect(url_for("storage"))

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    local_path = os.path.join(upload_dir, file.filename)
    file.save(local_path)

    result = upload_file_to_supabase(local_path, file.filename)

    if result.get("status") == "success":
        flash("Upload berhasil!", "success")
    else:
        flash("Gagal upload!", "danger")

    return redirect(url_for("storage"))

init_db(app)
app.register_blueprint(auth_blueprint, url_prefix="/auth")

@app.route("/delete_schedule/<id>")
def delete_schedule_route(id):
    if "user" not in session:
        return redirect(url_for("auth.login"))
    from supabase import delete_schedule
    ok = delete_schedule(id)
    flash("Jadwal berhasil dihapus!" if ok else "Gagal menghapus jadwal!", 
         "success" if ok else "danger")
    return redirect(url_for("scheduled"))

@app.route("/schedule/create", methods=["POST"])
def schedule_create():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    from supabase import insert_schedule

    data = {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "visibility": request.form.get("visibility"),
        "scheduled_at": request.form.get("scheduled_at"),
        "duration_minutes": int(request.form.get("duration")),
        "looping": True if request.form.get("looping") == "on" else False,
        "file_url": request.form.get("selected_file"),
        "stream_key": request.form.get("stream_key"),
        "rtmp_url": request.form.get("rtmp_url"),
        "status": "pending"
    }

    save = insert_schedule(data)

    if save["status"] == "success":
        flash("Jadwal berhasil disimpan!", "success")
    else:
        flash("Gagal menyimpan jadwal!", "danger")

    return redirect(url_for("scheduled"))


# ----- START APSCHEDULER (FIX29) -----
import atexit, shutil
try:
    from scheduler import scheduler
    # Only start scheduler if env RUN_SCHEDULER not set to "0" or "false"
    run_sched = os.environ.get("RUN_SCHEDULER", "1").lower() not in ("0","false","no")
    if run_sched:
        try:
            if not getattr(scheduler, 'running', False):
                scheduler.start()
            print("[APP] APScheduler started (fix29).")
        except Exception as e:
            print("[APP] Failed starting APScheduler:", e)
    else:
        print("[APP] RUN_SCHEDULER disabled by environment variable.")
    atexit.register(lambda: getattr(scheduler, 'shutdown', lambda **k: None)(wait=False))
except Exception as e:
    print("[APP] Scheduler import error (fix29):", e)
# ----- END APSCHEDULER (FIX29) -----


# --- FIX30 FORCE START SCHEDULER ---
import atexit
try:
    from scheduler import scheduler
    if not getattr(scheduler,'running',False):
        scheduler.start()
    print("[APP] APScheduler started (fix30)")
    atexit.register(lambda: scheduler.shutdown(wait=False))
except Exception as e:
    print("[APP] Scheduler start error (fix30):", e)
# --- END FIX30 ---

if __name__ == "__main__":
    try:
        scheduler.start()
    except Exception:
        pass
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
