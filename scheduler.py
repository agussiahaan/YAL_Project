import time, subprocess, requests, os
from datetime import datetime
print("[FIX32] scheduler loaded")

class SchedulerManager:
    def __init__(self, storage):
        self.storage = storage
        self.jobs = []

    def start(self):
        print("[FIX32] Scheduler started")

    def schedule_stream(self, title, file_url, dt, duration, rtmp, stream_key):
        job = {
            "id": len(self.jobs)+1,
            "title": title,
            "file_url": file_url,
            "dt": dt,
            "duration": duration,
            "rtmp": rtmp,
            "stream_key": stream_key
        }
        self.jobs.append(job)
        print("[FIX32] Job added:", job)
        return job["id"]
