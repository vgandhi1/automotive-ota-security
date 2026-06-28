// Package metrics registers OTA orchestrator telemetry per plan-docs/observability.md.
// The presign-api exposes these series for Prometheus scraping; orchestrator logic
// will increment them when NATS/campaign paths land in-repo.
package metrics

import (
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// ActiveCampaigns is the number of campaigns currently executing.
var ActiveCampaigns = promauto.NewGauge(prometheus.GaugeOpts{
	Name: "ota_active_campaigns",
	Help: "The current number of active OTA campaigns",
})

// UpdateStatus counts vehicle updates by status and firmware version.
var UpdateStatus = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "ota_vehicle_updates_total",
	Help: "Total number of vehicle updates processed by status",
}, []string{"status", "firmware_version"})

// NATSProcessingLatency tracks time to process incoming status updates from the edge (seconds).
var NATSProcessingLatency = promauto.NewHistogram(prometheus.HistogramOpts{
	Name:    "ota_nats_processing_latency",
	Help:    "Time in seconds to process incoming vehicle status updates from NATS",
	Buckets: []float64{.0005, .001, .0025, .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10},
})

// SetActiveCampaigns sets the active campaign gauge (orchestrator use).
func SetActiveCampaigns(n float64) {
	ActiveCampaigns.Set(n)
}

// RecordVehicleStatus increments the vehicle update counter for a status label.
func RecordVehicleStatus(status, firmwareVersion string) {
	UpdateStatus.WithLabelValues(status, firmwareVersion).Inc()
}

// ObserveNATSProcessingLatency records one NATS message handling duration.
func ObserveNATSProcessingLatency(d time.Duration) {
	NATSProcessingLatency.Observe(d.Seconds())
}
