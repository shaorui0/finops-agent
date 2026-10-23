## ADDED Requirements

### Requirement: Prometheus-compatible API
The server SHALL implement `/api/v1/query`, `/api/v1/query_range`, `/api/v1/series`, `/api/v1/labels`, `/api/v1/label/<name>/values` and `/api/v1/metadata` with Prometheus response shapes.

#### Scenario: Instant query
- **WHEN** a client queries `sum by (status) (increase(ingest_jobs_total[1d]))`
- **THEN** the response is a `vector` with one sample per status

### Requirement: Unsupported PromQL is an error, not a guess
Expressions outside the documented subset SHALL return HTTP 400 with `errorType: bad_data`.

#### Scenario: Unsupported function
- **WHEN** a client queries `histogram_quantile(0.9, x)`
- **THEN** the server returns 400 `bad_data`

### Requirement: Planted visibility gaps
The server SHALL NOT expose memory utilization for any instance.

#### Scenario: Memory missing
- **WHEN** a client lists `__name__` values
- **THEN** no metric name contains `mem`
