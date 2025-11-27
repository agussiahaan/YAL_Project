import requests

print("[FIX32] Supabase client loaded")

class SupabaseStorage:
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def list_files(self):
        return []

    def upload_file(self, local_path, filename):
        return True
