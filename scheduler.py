import subprocess
import requests
import os
import shutil
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import get_pending_schedules, update_schedule_status, history_start, history_finish

# timezone handling - read TZ env or default to Asia/Jakarta
try:
    from zoneinfo import ZoneInfo
    TZ_NAME = os.getenv('YAL_TIMEZONE', os.getenv('TZ', 'Asia/Jakarta'))
    LOCAL_TZ = ZoneInfo(TZ_NAME)
except Exception:
    LOCAL_TZ = timezone.utc

def make_aware_to_utc(dt):
    # dt can be naive or aware. Return aware UTC datetime.
    if dt is None:
        return None
    if dt.tzinfo is None:
        try:
            # assume local timezone
            return dt.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        except Exception:
            return dt.replace(tzinfo=timezone.utc)
    else:
        return dt.astimezone(timezone.utc)

def is_ffmpeg_available():
    return shutil.which("ffmpeg") is not None

def run_stream_job():
    print("[scheduler] Checking schedules...")
    if not is_ffmpeg_available():
        print("[scheduler] WARNING: ffmpeg not found in PATH. Streaming will fail if triggered.")
    try:
        schedules = get_pending_schedules()
    except Exception as e:
        print("[scheduler] Failed to fetch schedules:", e)
        return

    now = datetime.now(timezone.utc)
    print(f"[scheduler] now (UTC) = {now.isoformat()} - found {len(schedules)} pending schedules")

    for s in schedules:
        sid = s.get("id")
        try:
            raw = s.get("scheduled_at")
            if not raw:
                print("[scheduler] schedule missing scheduled_at for", sid)
                continue
            # parse ISO variants robustly
            try:
                sched_time = datetime.fromisoformat(raw)
            except Exception:
                try:
                    sched_time = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S%z")
                except Exception:
                    try:
                        # fallback: add seconds if missing
                        sched_time = datetime.fromisoformat(raw + ":00")
                    except Exception as e:
                        print("[scheduler] Could not parse scheduled_at for", sid, "raw:", raw, "err:", e)
                        continue

            sched_time_utc = make_aware_to_utc(sched_time)
            print(f"[scheduler] schedule {sid} scheduled_at (UTC) = {sched_time_utc.isoformat()} (raw: {raw})")

            # if it's time to run (now >= scheduled time)
            if now >= sched_time_utc:
                title = s.get("title")
                print(f"[scheduler] Triggering schedule {sid} - {title}")
                ok = update_schedule_status(sid, "running")
                if not ok:
                    print("[scheduler] Failed to mark running, skipping:", sid)
                    continue

                history_id = None
                try:
                    history_id = history_start(s)
                except Exception as e:
                    print('[scheduler] history_start failed:', e)

                try:
                    # Download file
                    file_url = s.get("file_url")
                    local_file = f"/tmp/{sid}.mp4"
                    print("[scheduler] Downloading file:", file_url)
                    r = requests.get(file_url, timeout=60)
                    if r.status_code != 200:
                        print("[scheduler] Failed to download file:", r.status_code, r.text if hasattr(r, 'text') else '')
                        update_schedule_status(sid, "failed")
                        try:
                            if history_id:
                                history_finish(history_id, 'failed', log='download_failed')
                        except Exception:
                            pass
                        continue
                    with open(local_file, "wb") as fh:
                        fh.write(r.content)

                    # Prepare ffmpeg command
                    duration_seconds = int(s.get("duration_minutes") or 0) * 60
                    looping = s.get("looping") in (True, "true", "True", "on", 1, "1")
                    loop_cmd = ["-stream_loop", "-1"] if looping else []
                    rtmp_url = (s.get("rtmp_url") or "").rstrip("/")
                    stream_key = s.get("stream_key") or ""
                    if not rtmp_url or not stream_key:
                        print("[scheduler] Missing RTMP or stream key for", sid)
                        update_schedule_status(sid, "failed")
                        try:
                            if history_id:
                                history_finish(history_id, 'failed', log='missing_rtmp_or_key')
                        except Exception:
                            pass
                        continue
                    rtmp = f"{rtmp_url}/{stream_key}"

                    # check ffmpeg availability
                    if not is_ffmpeg_available():
                        print("[scheduler] ffmpeg not available, cannot stream. Marking failed.")
                        update_schedule_status(sid, "failed")
                        try:
                            if history_id:
                                history_finish(history_id, 'failed', log='ffmpeg_not_found')
                        except Exception:
                            pass
                        continue

                    cmd = [
                        "ffmpeg",
                        "-re",
                        "-i", local_file,
                        *loop_cmd,
                        "-c", "copy",
                    ]
                    if duration_seconds > 0:
                        cmd += ["-t", str(duration_seconds)]
                    cmd += ["-f", "flv", rtmp]

                    print("[scheduler] Running ffmpeg:", " ".join(cmd))
                    # Run ffmpeg (blocking)
                    proc = subprocess.run(cmd, check=False)
                    print("[scheduler] ffmpeg finished for", sid, "returncode:", proc.returncode)

                    if proc.returncode != 0:
                        print("[scheduler] ffmpeg reported non-zero exit code:", proc.returncode)
                        update_schedule_status(sid, "failed")
                        try:
                            if history_id:
                                history_finish(history_id, 'failed', log=f'ffmpeg_rc_{proc.returncode}')
                        except Exception:
                            pass
                    else:
                        # mark finished
                        update_schedule_status(sid, "finished")
                        try:
                            if history_id:
                                history_finish(history_id, 'finished')
                        except Exception as e:
                            print('[scheduler] history_finish failed:', e)

                except Exception as ex:
                    print("[scheduler] Error while streaming:", ex)
                    update_schedule_status(sid, "failed")
                    try:
                        if history_id:
                            history_finish(history_id, 'failed', log=str(ex))
                    except Exception as e:
                        print('[scheduler] history_finish on except failed:', e)
                finally:
                    # cleanup
                    try:
                        if os.path.exists(local_file):
                            os.remove(local_file)
                    except Exception:
                        pass

        except Exception as e:
            print("[scheduler] Unexpected error processing schedule", sid if 'sid' in locals() else None, ":", e)

# create and configure scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(run_stream_job, "interval", seconds=30, id="yal_run_stream_job", max_instances=1)
