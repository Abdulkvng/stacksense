import urllib.request
import json
import sys

def main():
    repo = "Abdulkvng/stacksense"
    url = f"https://api.github.com/repos/{repo}/actions/runs?status=failure&per_page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print("Failed to fetch runs:", e)
        return

    runs = data.get("workflow_runs", [])
    if not runs:
        print("No failing runs found.")
        return

    run = runs[0]
    run_id = run["id"]
    print(f"Found failing run {run_id} for commit {run['head_sha']}")
    
    jobs_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
    req_jobs = urllib.request.Request(jobs_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req_jobs) as jresp:
            jobs_data = json.loads(jresp.read().decode())
    except Exception as e:
        print("Failed to fetch jobs:", e)
        return
        
    for job in jobs_data.get("jobs", []):
        if job["conclusion"] == "failure":
            print(f"\n--- Job: {job['name']} ---")
            for step in job["steps"]:
                if step["conclusion"] == "failure":
                    print(f"FAILED STEP: {step['name']}")

if __name__ == "__main__":
    main()
