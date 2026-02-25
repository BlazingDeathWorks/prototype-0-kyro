from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import uuid
import os
import shutil
import asyncio
from pathlib import Path

# Import the worker
from .worker import JobWorker, jobs

app = FastAPI(title="Project Kyro API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = Path("resume")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Global semaphore for worker concurrency
# max 4 urls concurrently across ALL jobs (or per job? User said "deploy that many worker based on the number of urls at max deploy 4 workers")
# Assuming global limit of 4 active browsers for resource safety.
MAX_WORKERS = 8
semaphore = asyncio.Semaphore(MAX_WORKERS)

async def process_job(job_id: str):
    """Background task to run the job with semaphore"""
    if job_id in jobs:
        await jobs[job_id].run(semaphore)

@app.post("/apply")
async def apply_to_jobs(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    urls: str = Form(...)
):
    """
    Submit a resume and list of URLs to apply to.
    urls: comma or newline separated string of URLs.
    """
    # Generate Job ID
    job_id = str(uuid.uuid4())
    
    # Save Resume
    resume_path = UPLOAD_DIR / f"{job_id}_{resume.filename}"
    with open(resume_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)
    
    # Parse URLs
    # Split by newline or comma and strip whitespace
    url_list = [u.strip() for u in urls.replace(',', '\n').split('\n') if u.strip()]
    
    if not url_list:
        raise HTTPException(status_code=400, detail="No valid URLs provided")
    
    # Create Worker
    worker = JobWorker(job_id, str(resume_path.absolute()), url_list)
    jobs[job_id] = worker
    
    # Start Background Task
    background_tasks.add_task(process_job, job_id)
    
    return {
        "job_id": job_id,
        "message": f"Started processing {len(url_list)} applications",
        "urls": url_list
    }

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a specific job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    worker = jobs[job_id]
    return {
        "job_id": job_id,
        "status": worker.status,
        "logs": worker.logs,
        "session_ids": worker.session_ids,
        "live_view_urls": worker.live_view_urls
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
