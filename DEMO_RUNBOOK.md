# NEXUS AI DevOps Optimizer — Professor Demo Runbook

## 1. Architecture — 30 seconds

Say:

> NEXUS connects GitHub, Jenkins, automated tests, Docker and application health checks. Its AI layer uses the real Jenkins evidence to optimize pipeline performance, prevent recurring failures and explain DevOps operations.

## 2. Prove the CI/CD pipeline — 90 seconds

Open Jenkins `NEXUS-CI-CD` and a successful build.

Show:

- Git checkout
- dependency installation
- parallel tests
- JUnit result
- Docker build
- Docker deployment
- `/health` verification
- `Finished: SUCCESS`

## 3. Prove NEXUS uses real data — 45 seconds

Open NEXUS and show:

- Jenkins connected
- latest build number
- recent build history
- success rate
- average build time
- service health

Say:

> These records come from the Jenkins REST API; they are not hardcoded dashboard values.

## 4. AI performance optimization — 2 minutes

Open **AI DEVOPS OPTIMIZATION**.

Show the measured bottleneck and recommendations.

Click **GENERATE AI PERFORMANCE ANALYSIS** and paste into ChatGPT.

Ask ChatGPT to prioritize safe, measurable improvements.

Important: distinguish observed Jenkins data from AI recommendations.

## 5. Benchmark — 90 seconds

Capture an existing real build as:

`Baseline`

Implement one justified optimization.

Run Jenkins again.

Capture the new real build as:

`Optimized`

Show the measured before/after percentage.

Do not claim improvement unless the measured result supports it.

## 6. AI failure prevention — 60 seconds

If a failed build exists, click **ANALYZE FAILURE PATTERNS**.

Paste into ChatGPT.

Explain that the AI is looking across real failed builds for recurring failure modes and preventive controls.

## 7. AI learning — 45 seconds

Click **EXPLAIN PIPELINE WITH AI**.

Show how the actual Jenkinsfile becomes a learning/viva assistant.

## 8. Optional RCA — 60 seconds

For a real failed build:

- Fetch real log
- Copy RCA prompt
- Paste into ChatGPT
- Show exact failed stage, evidence, root cause, correction and prevention

## Closing

> NEXUS creates a feedback loop: observe real DevOps data, use AI to recommend an optimization, implement it, rerun the real pipeline, and measure the result. That makes AI part of the DevOps engineering workflow rather than just a chatbot.
