import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BENCHMARK_FILE = DATA_DIR / "benchmarks.json"
START_TIME = time.time()

app = Flask(__name__)

JENKINS_URL = os.getenv("JENKINS_URL", "").rstrip("/")
JENKINS_USER = os.getenv("JENKINS_USER", "")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")
JENKINS_JOB = os.getenv("JENKINS_JOB", "NEXUS-CI-CD")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")

STAGE_ORDER = ["Checkout", "Install", "Test", "Docker Build", "Deploy", "Health Check"]
STAGE_ALIASES = {
    "Checkout": ["Checkout"],
    "Install": ["Install"],
    "Test": ["Test", "Application Tests", "Jenkins Integration Tests"],
    "Docker Build": ["Docker Build", "Build Docker Image"],
    "Deploy": ["Deploy"],
    "Health Check": ["Health Check", "Verify", "Health"]
}


def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not BENCHMARK_FILE.exists():
        BENCHMARK_FILE.write_text("[]", encoding="utf-8")


def load_benchmarks():
    ensure_data_file()
    try:
        return json.loads(BENCHMARK_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def save_benchmarks(items):
    ensure_data_file()
    BENCHMARK_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def jenkins_configured():
    return bool(JENKINS_URL and JENKINS_USER and JENKINS_TOKEN)


def jenkins_get(path, params=None):
    if not jenkins_configured():
        return None, "Jenkins credentials are not configured."
    try:
        response = requests.get(
            f"{JENKINS_URL}{path}",
            params=params,
            auth=(JENKINS_USER, JENKINS_TOKEN),
            timeout=8,
        )
        response.raise_for_status()
        return response, None
    except requests.RequestException as exc:
        return None, str(exc)


def job_path():
    return f"/job/{quote(JENKINS_JOB, safe='')}"


def normalize_stage_name(name):
    raw = (name or "").strip()
    for canonical, aliases in STAGE_ALIASES.items():
        if raw in aliases:
            return canonical
    return raw


def get_builds(limit=15):
    response, error = jenkins_get(
        f"{job_path()}/api/json",
        {"tree": "builds[number,result,duration,timestamp,building,url,displayName]"},
    )
    if error:
        return [], error
    builds = response.json().get("builds", [])[:limit]
    for build in builds:
        if build.get("duration") is not None:
            build["duration_seconds"] = round(build["duration"] / 1000, 1)
        if build.get("timestamp"):
            build["timestamp_iso"] = datetime.fromtimestamp(
                build["timestamp"] / 1000, tz=timezone.utc
            ).isoformat()
    return builds, None


def get_stage_data(build_number):
    response, error = jenkins_get(f"{job_path()}/{build_number}/wfapi/describe")
    if error:
        return {"available": False, "build_number": build_number, "stages": [], "error": error}
    data = response.json()
    stages = []
    for item in data.get("stages", []):
        stages.append({
            "name": normalize_stage_name(item.get("name")),
            "raw_name": item.get("name"),
            "status": item.get("status"),
            "duration_seconds": round((item.get("durationMillis") or 0) / 1000, 1),
            "duration_millis": item.get("durationMillis") or 0,
        })
    return {
        "available": True,
        "build_number": build_number,
        "status": data.get("status"),
        "stages": stages,
    }


def build_analytics(builds, stage_data=None):
    completed = [b for b in builds if not b.get("building") and b.get("result")]
    durations = [b.get("duration_seconds") for b in completed if b.get("duration_seconds") is not None]
    successful = [b for b in completed if b.get("result") == "SUCCESS"]
    failures = [b for b in completed if b.get("result") != "SUCCESS"]
    avg = round(sum(durations) / len(durations), 1) if durations else None
    latest = completed[0] if completed else (builds[0] if builds else None)

    failure_counts = {}
    for b in completed:
        if b.get("result") != "SUCCESS":
            failure_counts[b.get("result") or "UNKNOWN"] = failure_counts.get(b.get("result") or "UNKNOWN", 0) + 1

    stages = (stage_data or {}).get("stages", [])
    stage_total = sum(s.get("duration_seconds", 0) for s in stages)
    bottleneck = max(stages, key=lambda s: s.get("duration_seconds", 0), default=None)

    return {
        "sample_size": len(completed),
        "success_rate": round(len(successful) / len(completed) * 100, 1) if completed else None,
        "avg_duration_seconds": avg,
        "latest_duration_seconds": latest.get("duration_seconds") if latest else None,
        "latest_build": latest.get("number") if latest else None,
        "failure_count": len(failures),
        "failure_distribution": failure_counts,
        "stage_total_seconds": round(stage_total, 1),
        "bottleneck": bottleneck,
        "stages": stages,
    }


def generate_recommendations(analytics):
    recs = []
    bottleneck = analytics.get("bottleneck")
    if bottleneck:
        name = bottleneck.get("name", "Unknown stage")
        seconds = bottleneck.get("duration_seconds", 0)
        total = analytics.get("stage_total_seconds") or 0
        share = round(seconds / total * 100, 1) if total else 0
        recs.append({
            "priority": "HIGH",
            "title": f"Investigate {name} bottleneck",
            "detail": f"It accounts for about {share}% of the measured stage time ({seconds:.1f}s). Optimize this stage first.",
        })

    if analytics.get("sample_size", 0) >= 3 and analytics.get("success_rate") is not None and analytics["success_rate"] < 90:
        recs.append({
            "priority": "HIGH",
            "title": "Address recurring pipeline failures",
            "detail": f"Recent success rate is {analytics['success_rate']:.1f}%. Use the failure distribution and real console logs to target the dominant failure mode.",
        })

    recs.extend([
        {"priority": "MEDIUM", "title": "Cache dependencies", "detail": "Cache Python package downloads or use a controlled dependency cache to reduce repeated install time."},
        {"priority": "MEDIUM", "title": "Use efficient Docker builds", "detail": "Keep dependency layers stable and evaluate BuildKit/buildx caching for repeat builds."},
        {"priority": "LOW", "title": "Keep independent checks parallel", "detail": "Application tests and Jenkins integration tests are independent quality gates and can run concurrently."},
    ])
    return recs[:5]


def parse_stage_markers(console):
    """Best-effort fallback for Jenkins installations without Workflow API."""
    matches = []
    pattern = re.compile(r"\[Pipeline\]\s*\{ \(([^)]+)\)")
    for match in pattern.finditer(console or ""):
        matches.append(normalize_stage_name(match.group(1)))
    unique = []
    for item in matches:
        if item not in unique:
            unique.append(item)
    return [{"name": x, "status": "UNKNOWN", "duration_seconds": 0} for x in unique]


@app.get("/")
def index():
    return render_template(
        "index.html",
        job=JENKINS_JOB,
        jenkins_url=JENKINS_URL,
        app_version=APP_VERSION,
    )


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "nexus-ai-devops-optimizer",
        "version": APP_VERSION,
        "uptime_seconds": int(time.time() - START_TIME),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/jenkins/overview")
def jenkins_overview():
    response, error = jenkins_get(
        f"{job_path()}/api/json",
        {"tree": "name,url,color,lastBuild[number,result,duration,timestamp,building,url,displayName],lastSuccessfulBuild[number,result,duration,timestamp,url],lastFailedBuild[number,result,duration,timestamp,url]"},
    )
    if error:
        return jsonify({"connected": False, "configured": jenkins_configured(), "error": error, "job": JENKINS_JOB, "jenkins_url": JENKINS_URL})
    return jsonify({"connected": True, "configured": True, "job": response.json(), "job_name": JENKINS_JOB, "jenkins_url": JENKINS_URL})


@app.get("/api/jenkins/builds")
def jenkins_builds():
    builds, error = get_builds()
    if error:
        return jsonify({"connected": False, "configured": jenkins_configured(), "error": error, "builds": []})
    return jsonify({"connected": True, "builds": builds, "job_name": JENKINS_JOB})


@app.get("/api/jenkins/console/latest")
def latest_console():
    response, error = jenkins_get(f"{job_path()}/api/json", {"tree": "lastBuild[number,result,building]"})
    if error:
        return jsonify({"connected": False, "error": error}), 503
    build = response.json().get("lastBuild")
    if not build:
        return jsonify({"connected": True, "message": "No Jenkins builds exist yet.", "console": ""})
    console_response, error = jenkins_get(f"{job_path()}/{build['number']}/consoleText")
    if error:
        return jsonify({"connected": False, "error": error}), 503
    return jsonify({"connected": True, "build_number": build["number"], "result": build.get("result"), "building": build.get("building", False), "console": console_response.text})


@app.get("/api/jenkins/stages/<int:build_number>")
def jenkins_stages(build_number):
    data = get_stage_data(build_number)
    if not data["available"]:
        return jsonify(data)
    return jsonify(data)


@app.get("/api/ai/analytics")
def ai_analytics():
    builds, error = get_builds()
    if error:
        return jsonify({"connected": False, "error": error}), 503

    build_number = request.args.get("build", type=int) or (builds[0]["number"] if builds else None)
    stage_data = get_stage_data(build_number) if build_number else {"available": False, "stages": []}
    if not stage_data.get("stages") and build_number:
        console_response, console_error = jenkins_get(f"{job_path()}/{build_number}/consoleText")
        if not console_error:
            stage_data["stages"] = parse_stage_markers(console_response.text)
            stage_data["fallback"] = True

    analytics = build_analytics(builds, stage_data)
    analytics["recommendations"] = generate_recommendations(analytics)
    analytics["jenkins_job"] = JENKINS_JOB
    analytics["build_number"] = build_number
    analytics["stage_api_available"] = bool(stage_data.get("available"))
    return jsonify(analytics)


@app.get("/api/ai/insight-prompt")
def ai_insight_prompt():
    builds, error = get_builds()
    if error:
        return jsonify({"error": error}), 503
    build_number = request.args.get("build", type=int) or (builds[0]["number"] if builds else None)
    stage_data = get_stage_data(build_number) if build_number else {"stages": []}
    analytics = build_analytics(builds, stage_data)
    source = ""
    try:
        source = (BASE_DIR / "Jenkinsfile").read_text(encoding="utf-8")
    except OSError:
        pass
    prompt = f"""You are an AI DevOps/SRE optimization engineer. Analyze the REAL Jenkins performance data below.
Goal: improve DevOps operations, pipeline efficiency, reliability and system performance without removing quality gates or changing the deployment target.

Return:
1. The main measurable bottleneck.
2. Three prioritized optimizations.
3. Which Jenkinsfile changes are safe to implement first and why.
4. How to benchmark the change fairly.
5. Risks/trade-offs.
Do not invent metrics that are not supplied.

REAL JENKINS JOB: {JENKINS_JOB}
REAL BUILD SAMPLE: {json.dumps(builds, indent=2)}
REAL STAGE DATA: {json.dumps(stage_data.get('stages', []), indent=2)}
CALCULATED ANALYTICS: {json.dumps(analytics, indent=2)}

CURRENT JENKINSFILE:
{source}
"""
    return jsonify({"prompt": prompt, "analytics": analytics})


@app.get("/api/ai/failure-prompt")
def ai_failure_prompt():
    builds, error = get_builds()
    if error:
        return jsonify({"error": error}), 503
    failures = [b for b in builds if b.get("result") not in ("SUCCESS", None) and not b.get("building")]
    evidence = []
    for build in failures[:5]:
        response, console_error = jenkins_get(f"{job_path()}/{build['number']}/consoleText")
        if not console_error:
            evidence.append({"build": build["number"], "result": build.get("result"), "console": response.text[-12000:]})
    prompt = f"""You are an AI SRE failure-prevention engineer. Analyze the REAL failed Jenkins builds below.
Identify recurring failure patterns, likely preventive controls, and the smallest safe Jenkins/application improvements.
Separate observed evidence from inference. Do not invent missing information.

JOB: {JENKINS_JOB}
FAILED BUILDS:
{json.dumps(evidence, indent=2)}
"""
    return jsonify({"prompt": prompt, "failed_builds": [b.get("number") for b in failures[:5]]})


@app.get("/api/ai/learning-prompt")
def ai_learning_prompt():
    try:
        source = (BASE_DIR / "Jenkinsfile").read_text(encoding="utf-8")
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500
    prompt = f"""Act as a DevOps mentor. Explain this REAL Jenkinsfile to a final-year engineering student.
Explain each stage, why it exists, what failure it prevents, how it connects to CI/CD, Docker and deployment, and what metrics should be monitored.
Then give 5 viva questions with concise answers. Stay strictly grounded in the Jenkinsfile.

JENKINSFILE:
{source}
"""
    return jsonify({"prompt": prompt})


@app.get("/api/ai/optimization-prompt")
def ai_optimization_prompt():
    try:
        source = (BASE_DIR / "Jenkinsfile").read_text(encoding="utf-8")
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"prompt": f"""You are a senior DevOps engineer optimizing a Jenkins CI/CD pipeline.
Review the REAL Jenkinsfile below. Optimize for shorter build time, safe parallel execution, dependency caching, reliable test reporting, timeouts, cleanup, clear diagnostics, and efficient Docker builds.
Preserve application behavior, deployment target and all quality gates. Return an improved Jenkinsfile and explain every change, including expected performance impact and risks.
Do not invent tools that are unavailable on a Windows Jenkins agent.

JENKINSFILE:
{source}"""})


@app.get("/api/pipeline-source")
def pipeline_source():
    try:
        return jsonify({"source": (BASE_DIR / "Jenkinsfile").read_text(encoding="utf-8")})
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/api/benchmarks")
def benchmarks():
    return jsonify({"benchmarks": load_benchmarks()})


@app.post("/api/benchmarks")
def add_benchmark():
    payload = request.get_json(silent=True) or {}
    if not payload.get("label") or payload.get("build_number") is None:
        return jsonify({"error": "label and build_number are required"}), 400
    items = load_benchmarks()
    item = {
        "label": str(payload["label"]),
        "build_number": int(payload["build_number"]),
        "duration_seconds": payload.get("duration_seconds"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "note": payload.get("note", ""),
    }
    items.append(item)
    save_benchmarks(items[-20:])
    return jsonify({"saved": item, "benchmarks": load_benchmarks()}), 201


@app.delete("/api/benchmarks")
def clear_benchmarks():
    save_benchmarks([])
    return jsonify({"benchmarks": []})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
