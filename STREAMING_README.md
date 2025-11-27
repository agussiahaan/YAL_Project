
FFmpeg Auto-Streaming Notes
===========================

- This project includes a scheduler that checks Supabase `schedules` table every 30s
  and runs ffmpeg to stream when schedule time >= now.

- Railway may stop long-running processes on free tiers. For production, consider
  running the streaming worker on a dedicated server/container or use a managed worker.

- Dockerfile includes ffmpeg installation. Make sure your deployment environment
  allows running ffmpeg and has sufficient resources.

