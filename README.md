# NEXUS — AI DevOps Optimizer

NEXUS is a real DevOps control and optimization workspace built around a real GitHub → Jenkins → pytest → Docker → deployment → health-check pipeline. Its AI layer is designed to optimize DevOps operations rather than merely provide a chatbot.

## What the AI actually does

1. **Pipeline Performance Optimization** — NEXUS reads real Jenkins build history and Workflow API stage timings, calculates success rate, average build time and the measured bottleneck, then generates an evidence-rich ChatGPT optimization prompt.
2. **Jenkinsfile Optimization** — ChatGPT reviews the real Jenkinsfile and proposes safer parallelism, caching, timeouts, diagnostics, cleanup and Docker-build improvements while preserving quality gates and deployment behavior.
3. **Failure Prevention** — NEXUS collects recent failed Jenkins console logs and asks ChatGPT to identify recurring failure patterns and preventive controls.
4. **DevOps Learning** — ChatGPT explains the real Jenkinsfile stage by stage and generates viva questions, connecting implementation to CI/CD, Docker and deployment.
5. **Measured Benchmarking** — NEXUS can capture real Jenkins builds as baseline/optimized measurements and calculate the observed improvement in build duration.
6. **Root Cause Analysis** — For a real failed build, NEXUS fetches the actual Jenkins console and prepares a structured RCA prompt.

NEXUS never fabricates Jenkins builds, stage timings or performance improvements. AI recommendations are presented as recommendations until they are implemented and measured.

## Architecture

```text
GitHub
  ↓ push / webhook
Jenkins
  ↓
Checkout → Install → Parallel Tests → Docker Build → Deploy → Health Check
  ↓                         ↓
real build history       real console logs
  ↓                         ↓
NEXUS analytics ───────────→ ChatGPT
        ↓                      ↓
 performance bottleneck   optimization / RCA / learning
        ↓
 implement → rerun Jenkins → benchmark before vs after
```

## Local setup

1. Create `.env` from `.env.example` and keep the Jenkins token private.
2. Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run NEXUS on a port that is not occupied by the deployed container. Example:

```powershell
$env:PORT=5055
python -m app.app
```

4. Open `http://127.0.0.1:5055`.

## Jenkins configuration

The current project is designed for the Windows Jenkins agent used in the demonstration. Set:

```text
JENKINS_URL=http://localhost:8181
JENKINS_USER=admin
JENKINS_TOKEN=<your existing token>
JENKINS_JOB=NEXUS-CI-CD
```

Do not commit `.env`.

## AI demonstration

### A. Performance optimization

1. Open NEXUS and show real build history.
2. Show the AI bottleneck and recommendations calculated from Jenkins evidence.
3. Click **GENERATE AI PERFORMANCE ANALYSIS**.
4. Paste the prompt into ChatGPT.
5. Ask ChatGPT to prioritize safe changes.
6. Implement one selected change in the Jenkinsfile.
7. Run Jenkins again.
8. Capture the old build as **Baseline** and the new build as **Optimized**.
9. Show the measured before/after result in Benchmark Lab.

### B. Failure prevention

1. Have at least one real failed build in Jenkins history.
2. Click **ANALYZE FAILURE PATTERNS**.
3. Paste the generated prompt into ChatGPT.
4. Discuss recurring causes and preventive controls.

### C. Learning

Click **EXPLAIN PIPELINE WITH AI** and paste the generated prompt into ChatGPT. This turns the actual Jenkinsfile into a DevOps learning/viva assistant.

### D. Root cause analysis

For a real failed build, click **FETCH REAL LOG**, then **COPY RCA PROMPT**, and paste it into ChatGPT. The prompt explicitly requires evidence-based RCA and prohibits invented information.

## Benchmarking rule

Do not claim an improvement before measuring it. Use comparable Jenkins builds and report the actual measured duration. If the optimized build is slower, NEXUS should display that honestly.

## Demo closing statement

> NEXUS uses real Jenkins CI/CD data as an engineering feedback loop. AI analyzes measured pipeline performance, identifies optimization opportunities, explains DevOps operations, detects recurring failure patterns and supports evidence-based changes. The effect of an optimization is then validated by running the real pipeline again and comparing measured results.
