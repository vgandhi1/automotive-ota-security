# Observability & Monitoring: Overdrive OTA Manager

## 1. The Observability Strategy
In a distributed fleet environment, pushing firmware to 50,000+ vehicles simultaneously creates massive data streams. To safely manage "Blast Radius" and perform systematic Root Cause Analysis, the Overdrive OTA Manager implements the "Three Pillars of Observability" with a strong focus on real-time metrics.

* **Metrics (Prometheus):** Tracks quantitative data such as active campaigns, success/failure rates, and NATS queue depth.
* **Visualization (Grafana):** Provides a centralized, real-time command center for fleet managers to monitor OTA health.
* **Structured Logging (JSON):** Contextual logs injected with `CampaignID` and `VIN` to trace exact failure points.

## 2. Key Telemetry Tracked
To ensure functional safety and platform stability, the Go Orchestrator exposes the following custom metrics:
* `ota_active_campaigns` (Gauge): The number of campaigns currently executing.
* `ota_vehicle_updates_total` (Counter): Total updates processed, partitioned by status (`pending`, `downloading`, `success`, `failed`).
* `ota_nats_processing_latency` (Histogram): Time taken to process incoming status updates from the edge.

## 3. Go Microservice Instrumentation (Prometheus)
The Go backend exposes a `/metrics` endpoint using the official Prometheus client library.

```go
package metrics

import (
	"[github.com/prometheus/client_golang/prometheus](https://github.com/prometheus/client_golang/prometheus)"
	"[github.com/prometheus/client_golang/prometheus/promauto](https://github.com/prometheus/client_golang/prometheus/promauto)"
)

// 1. Define Custom Metrics
var (
	ActiveCampaigns = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "ota_active_campaigns",
		Help: "The current number of active OTA campaigns",
	})

	UpdateStatus = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ota_vehicle_updates_total",
		Help: "Total number of vehicle updates processed by status",
	}, []string{"status", "firmware_version"})
)

// 2. Increment Metrics in Business Logic
func RecordVehicleStatus(status string, fwVersion string) {
    UpdateStatus.WithLabelValues(status, fwVersion).Inc()
}