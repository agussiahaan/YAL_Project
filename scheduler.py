
# --- PATCHED scheduler.py (fix29) ---
import os, shutil, subprocess, requests, sys, traceback
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo(os.getenv("YAL_TIMEZONE", "Asia/Jakarta"))
except Exception:
    LOCAL_TZ = timezone.utc

from apscheduler.schedulers.background import BackgroundScheduler

print("[scheduler] module imported (fix29).")

def to_utc(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(timezone.utc)

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def run_stream_job_once(s):
    sid = s.get("id")
    print("[scheduler] Running job:", sid)
    try:
        url = s.get("file_url") or s.get("url") or s.get("source")
        print("[scheduler] file_url:", url)
        local = f"/tmp/{sid}.mp4"
        # download file
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(local, "wb") as fh:
            fh.write(r.content)
        print("[scheduler] downloaded to", local)
    except Exception as e:
        print("[scheduler] download failed:", e, file=sys.stderr)
        traceback.print_exc()
        return

    rtmp = s.get("rtmp_url", "").rstrip("/")
    key = s.get("stream_key", "") or s.get("stream_key_full", "")
    if not rtmp or not key:
        print("[scheduler] missing rtmp/key", rtmp, key)
        return
    out_rtmp = f"{rtmp}/{key}" if not (rtmp.endswith(key)) else rtmp

    dur_min = int(s.get("duration_minutes") or s.get("duration") or 30)
    dur_sec = dur_min * 60
    looping = s.get("looping") in (True, "true", "on", "1", 1, "yes")

    cmd = [
        "ffmpeg", "-y", "-re",
        "-stream_loop", "-1" if looping else "0",
        "-i", local,
        "-c:v", "libx264", "-preset", "veryfast", "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "flv", out_rtmp
    ]
    if dur_sec > 0:
        # -t must appear before -f so we insert earlier
        cmd.insert(5, "-t")
        cmd.insert(6, str(dur_sec))

    print("[scheduler] FFMPEG CMD:", " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        print("[scheduler] ffmpeg returncode:", p.returncode)
        if p.stdout:
            print("[scheduler] ffmpeg stdout:", p.stdout[:2000])
        if p.stderr:
            print("[scheduler] ffmpeg stderr:", p.stderr[:2000], file=sys.stderr)
    except Exception as e:
        print("[scheduler] failed to run ffmpeg:", e, file=sys.stderr)
    finally:
        try:
            os.remove(local)
        except Exception:
            pass

def run_stream_job():
    print("[scheduler] Checking pending schedules...")
    # Try to import supabase helpers if available
    try:
        from supabase import get_pending_schedules, update_schedule_status, history_start, history_finish
    except Exception as e:
        print("[scheduler] supabase helpers not available:", e)
        # fallback: nothing to do
        return

    try:
        pending = get_pending_schedules()
    except Exception as e:
        print("[scheduler] Error fetching schedules:", e)
        return

    now = datetime.now(timezone.utc)
    for s in pending:
        raw = s.get("scheduled_at")
        sched_utc = to_utc(raw)
        if sched_utc and sched_utc <= now:
            run_stream_job_once(s)

scheduler = BackgroundScheduler()
scheduler.add_job(run_stream_job, "interval", seconds=int(os.environ.get("SCHED_INTERVAL", "30")), max_instances=1)
print("[scheduler] jobs configured (fix29).")
