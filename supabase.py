import requests
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "yal-storage")

def upload_file_to_supabase(local_path, filename):
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{filename}"

    with open(local_path, 'rb') as f:
        file_data = f.read()

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream",
    }

    res = requests.post(url, headers=headers, data=file_data)

    if res.status_code in [200, 201]:
        return {"status": "success"}
    else:
        return {"status": "error", "message": res.text}




def get_public_url(name):
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{name}"

def list_files():
    url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    # Supabase requires prefix
    body = {
        "prefix": "",
        "limit": 200,
        "offset": 0
    }

    res = requests.post(url, headers=headers, json=body)
    if res.status_code == 200:
        return res.json()
    return []


def insert_schedule(data):
    import requests
    url = f"{SUPABASE_URL}/rest/v1/schedules"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, headers=headers, json=data)
    return {"status": "success" if r.status_code in [200,201] else "error", "detail": r.text}


def get_schedules():
    import requests
    url = f"{SUPABASE_URL}/rest/v1/schedules?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []

def delete_schedule(id):
    import requests
    url = f"{SUPABASE_URL}/rest/v1/schedules?id=eq.{id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    r = requests.delete(url, headers=headers)
    return r.status_code == 204


def get_pending_schedules():
    import requests
    url = f"{SUPABASE_URL}/rest/v1/schedules?status=eq.pending&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []

def update_schedule_status(id, status):
    import requests, json
    url = f"{SUPABASE_URL}/rest/v1/schedules?id=eq.{id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.patch(url, headers=headers, json={"status": status})
    return r.status_code in (200, 204)



def history_start(schedule):
    import requests, json
    url = f"{SUPABASE_URL}/rest/v1/stream_history"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "schedule_id": schedule.get("id"),
        "title": schedule.get("title"),
        "status": "running"
    }
    r = requests.post(url, headers=headers, json=data)
    if r.status_code in (200,201):
        try:
            # Supabase returns created row(s) as JSON when using REST with returning=representation; otherwise return None
            return r.json()[0].get("id") if isinstance(r.json(), list) and r.json() else None
        except Exception:
            return None
    return None

def history_finish(history_id, status="finished", log=""):
    import requests, json
    url = f"{SUPABASE_URL}/rest/v1/stream_history?id=eq.{history_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "end_time": "now()",
        "status": status,
        "log": log
    }
    r = requests.patch(url, headers=headers, json=data)
    return r.status_code in (200,204)

def get_history():
    import requests
    url = f"{SUPABASE_URL}/rest/v1/stream_history?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []
