# Hardware safety boundary

P0 contains no code that changes GPU power, launches workloads, or invokes sudo.
The HIL actuator is deliberately a placeholder.

Before P5, hardware mutation must be isolated behind an allow-listed service
that validates action IDs, GPU IDs, device-reported power ranges, temperatures,
telemetry freshness, and controller heartbeat. Every exit path must restore the
captured default power limits. Frozen policies only are permitted in HIL runs.
