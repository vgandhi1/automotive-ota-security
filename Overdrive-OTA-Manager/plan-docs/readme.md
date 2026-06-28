# Project Overdrive: Distributed Fleet OTA Campaign Manager

## Overview
Project Overdrive is an enterprise-grade Over-The-Air (OTA) software update orchestrator designed for connected vehicle fleets. It allows fleet managers to securely deploy, monitor, and manage firmware updates across thousands of distributed edge nodes (vehicles) simultaneously.

This system is built to handle the extreme data-intensive requirements of concurrent fleet updates, prioritizing fault tolerance, systematic troubleshooting, and blast-radius containment (Canary Deployments) to ensure functional safety during the vehicle lifecycle.

## Key Features
* **Decoupled Planes:** Separates the high-frequency Control Plane (NATS) from the heavy-payload Data Plane (HTTPS/CDN).
* **Canary Rollouts:** Automatically limits blast radius by deploying updates to a small test subset of vehicles before expanding to the entire fleet.
* **Real-Time State Tracking:** Ingests asynchronous status streams to maintain a live state machine for every vehicle in the campaign.
* **Idempotent Operations:** Prevents duplicate installations and bricked hardware through strict state validation.

## Technology Stack
* **Edge/Vehicle Simulator:** Rust (Simulating fleet connections and state transitions)
* **Control Plane Messaging:** NATS JetStream
* **Orchestrator Backend:** Go (Concurrent campaign management & state machine)
* **Payload Delivery (CDN):** AWS S3 / CloudFront (Simulated via LocalStack for development)
* **Database:** PostgreSQL (Relational campaign metadata) & Redis (High-speed state caching)
* **Frontend UI:** React.js, Redux, TypeScript, Styled Components