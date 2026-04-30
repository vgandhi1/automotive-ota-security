# Project Planning: Overdrive OTA Manager

## 1. Mission
To build a highly reliable, scalable, and distributed micro-services platform capable of securely pushing firmware updates to a simulated fleet of 50,000+ vehicles, enabling data-driven deployment strategies and mitigating rollout risks.

## 2. Development Phases

### Phase 1: Foundation & Payload Infrastructure (Data Plane)
* Set up Docker and Kubernetes orchestration.
* Implement an object storage system (AWS S3 or MinIO) to host the heavy firmware binary files (`.bin` payloads).
* Create an endpoint that generates secure, time-limited, pre-signed URLs for payload downloads.

### Phase 2: Edge Simulation & Control Plane (NATS)
* Deploy NATS JetStream for high-throughput messaging.
* Develop a Rust-based vehicle simulator capable of spinning up 1,000+ lightweight concurrent vehicle connections.
* Program the simulator to listen for "Update Available" commands, download the mock payload via HTTPS, and publish state transitions back to NATS (e.g., `Downloading -> Verifying -> Installing -> Complete`).

### Phase 3: The Campaign Orchestrator (Go Backend)
* Build the Go microservice that manages the OTA Campaigns.
* Implement a robust State Machine in Go to track the exact installation phase of every vehicle.
* Develop the "Canary Deployment" logic: The orchestrator targets 5% of the fleet, waits for a 99% success rate, and only then triggers the remaining 95%.

### Phase 4: Command Center Presentation Layer (React)
* Build a reactive web interface using React and TypeScript.
* Create a "Campaign Creation" flow (Select Firmware -> Select Target VINs -> Set Rollout Strategy).
* Develop a real-time dashboard visualizing the fleet's update progress using WebSocket subscriptions.

### Phase 5: Resiliency & Chaos Engineering
* Implement idempotent validation to ensure vehicles ignore duplicate update commands.
* Simulate network drops (vehicles driving through tunnels) to test the Go orchestrator's reconnection and retry queues.