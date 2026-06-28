# System Architecture: Overdrive OTA Manager

## 1. High-Level Topology
The system utilizes a split-plane architecture to manage the competing requirements of high-frequency status tracking and massive binary file distribution.

* **Control Plane:** NATS JetStream handles low-latency, asynchronous signaling.
* **Data Plane:** A CDN (Content Delivery Network) handles the distribution of massive firmware binaries.

## 2. Core Components

### The Go Orchestrator (The Brain)
* Exposes a GraphQL/REST API for the React frontend to create and monitor campaigns.
* Manages the overarching Campaign logic (Rollout percentages, pausing/aborting campaigns).
* Subscribes to the NATS `vehicle.status.*` topics to update the fleet state in real-time.
* Uses an in-memory state machine backed by Redis to rapidly track if a vehicle is `PENDING`, `DOWNLOADING`, `INSTALLING`, or `FAILED`.

### The NATS Message Broker (The Nervous System)
* **Topic: `fleet.command.update`**: The Go orchestrator publishes commands here. Vehicles subscribe to this topic to know when an update is ready. The message contains a pre-signed CDN URL, not the file itself.
* **Topic: `vehicle.status.{vin}`**: Vehicles publish their real-time installation progress back to the orchestrator.

### The Vehicle Simulators (The Edge)
* Written in Rust for high concurrency.
* Listens to NATS commands.
* Executes HTTP GET requests to the CDN to pull the payload.
* Simulates failure states (e.g., 2% of vehicles report a checksum verification failure to test the Orchestrator's error handling).

## 3. Distributed State Machine Flow
1.  **Initiation:** React UI requests a Campaign. Go Orchestrator saves Campaign to PostgreSQL.
2.  **Signaling:** Orchestrator publishes `UPDATE_AVAILABLE` to NATS with a secure S3 link.
3.  **Acknowledgment:** Vehicle receives message, transitions to `PENDING`, and publishes status to NATS.
4.  **Data Pull:** Vehicle connects directly to S3/CloudFront via HTTPS to download the payload. It publishes `DOWNLOADING: 50%` to NATS.
5.  **Execution:** Vehicle finishes download, verifies payload hash, and publishes `INSTALLING`.
6.  **Completion:** Vehicle simulates reboot and publishes `SUCCESS`. Orchestrator updates final database record.

## 4. Safety & Blast Radius Control
* **Phased Rollouts:** The Orchestrator automatically pauses if the `FAILED` state exceeds a 1% threshold during the Canary phase, protecting the broader fleet from bricked hardware.
* **Time-to-Live (TTL):** Pre-signed CDN URLs expire after 2 hours. If a vehicle loses connection and tries to download the payload days later, it is rejected, forcing it to re-authenticate with the Orchestrator to ensure the firmware is still valid.