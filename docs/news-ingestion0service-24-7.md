# 1.1 News Ingestion Service (24/7)

## Objective
Run a reliable 24/7 **economic-event + news** ingestion pipeline with:
- one active primary alert provider
- automatic failover to backup alert provider(s)
- enrichment from news headlines
- normalized output ready for downstream EUR/USD filtering, price-watch trigger, and storage

---

## Provider Strategy

### Selected Providers
- **Provider A (Primary Alerts): Trading Economics**
- **Provider B (Fallback Alerts): Secondary economic calendar provider (TBD at implementation)**
- **Provider C (Headline Enrichment): MarketAux or FMP**
- **Provider D (Official Context/Validation): FRED**

### Why this mix
- Trading Economics is used for low-latency event alerts (actual/forecast/previous style macro releases).
- Secondary calendar provider prevents single-point failure for alerting.
- MarketAux/FMP enriches reports with article/headline context.
- FRED provides trusted historical macro context and validation (not instant trigger source).

---

## Runtime Operating Mode

### Active/Standby model (alerts)
- Only **one alert provider** is active for triggering at a time.
- Preferred order: **A → B** for event alerts.
- If active alert provider is unhealthy, switch automatically.
- Periodically test whether higher-priority provider recovered, then fail back safely.

### Parallel enrichment model
- Headline enrichment provider (C) can run in parallel on polling.
- FRED (D) is queried on-demand or scheduled for context enrichment, not for release-second triggering.

### Failover policy (alerts)
Trigger failover when any persists beyond threshold:
- connection cannot be established
- heartbeat failures (for WS/stream mode)
- repeated timeout/rate-limit errors
- no new event messages for stale-window threshold during active market hours

---

## Connection Models

### Provider A (Trading Economics) — stream/poll mode per plan
- If streaming available on current plan:
  - persistent connection
  - heartbeat/ping-pong
  - reconnect with exponential backoff + jitter
  - resubscribe after reconnect
- If streaming not available:
  - short-interval polling with idempotent cursor/time-window
- If repeated failures exceed threshold: failover to B

### Provider B (Secondary calendar provider) — fallback alerts
- Connection model depends on provider capability:
  - WS/stream: persistent + heartbeat + reconnect
  - HTTP: interval polling + cursor/last_seen
- Must be production-ready for alert continuity when A fails

### Provider C (MarketAux/FMP) — HTTP enrichment
- Poll at configured interval
- Deduplicate by URL/content hash
- Retry with exponential backoff
- Respect rate limits and retry-after headers

### Provider D (FRED) — context/validation
- Scheduled/on-demand HTTP pulls for historical series
- No realtime trigger responsibility
- Used to enrich and validate macro significance in reports

---

## Unified Normalized Event Contract (output of ingestion)

### A) Economic event record (alert-capable)
- `event_id`
- `provider`
- `country`
- `currency`
- `event_name`
- `published_at`
- `actual`
- `forecast`
- `previous`
- `importance`
- `url`
- `raw_json`

### B) News enrichment record
- `source`
- `published_at`
- `title`
- `author`
- `content`
- `url`
- `raw_json`

### Common metadata
- `received_at`
- `ingestion_provider`
- `ingestion_channel` (`alerts|enrichment|context`)
- `ingestion_latency_ms`
- `dedup_hash`

---

## Reliability Rules

### Heartbeat (stream providers)
- ping interval: configurable
- pong timeout: configurable
- max missed pongs: configurable
- exceeding threshold triggers reconnect and possible failover

### Reconnect
- exponential backoff + jitter
- capped maximum delay
- reset attempt counter after stable period

### Storm prevention
- no tight retry loops
- bounded retries per time window
- cool-down/circuit-breaker for persistent auth or vendor failures

---

## Health & Observability

### Health fields (minimum)
- active alert provider
- alert provider state (`connected|reconnecting|degraded|stopped`)
- last event timestamp (alerts)
- last enrichment timestamp
- reconnect counts (1h/24h)
- failover/failback counts

### Structured log events (minimum)
- `connect_start`
- `connect_ok`
- `subscribe_ok`
- `event_received`
- `enrichment_received`
- `disconnect_detected`
- `reconnect_scheduled`
- `reconnect_success`
- `failover_triggered`
- `failback_triggered`

---

## Config Contract (.env)

### Provider A (Trading Economics)
- `NEWS_PROVIDER_A_ENABLED`
- `NEWS_PROVIDER_A_NAME=TradingEconomics`
- `NEWS_PROVIDER_A_PROTOCOL=ws|http`
- `NEWS_PROVIDER_A_URL`
- `NEWS_PROVIDER_A_API_KEY`
- `NEWS_PROVIDER_A_HEARTBEAT_INTERVAL_SECONDS` (if ws)
- `NEWS_PROVIDER_A_PONG_TIMEOUT_SECONDS` (if ws)
- `NEWS_PROVIDER_A_POLL_INTERVAL_SECONDS` (if http)

### Provider B (Secondary calendar fallback)
- `NEWS_PROVIDER_B_ENABLED`
- `NEWS_PROVIDER_B_NAME`
- `NEWS_PROVIDER_B_PROTOCOL=ws|http`
- `NEWS_PROVIDER_B_URL`
- `NEWS_PROVIDER_B_API_KEY`
- `NEWS_PROVIDER_B_HEARTBEAT_INTERVAL_SECONDS` (if ws)
- `NEWS_PROVIDER_B_PONG_TIMEOUT_SECONDS` (if ws)
- `NEWS_PROVIDER_B_POLL_INTERVAL_SECONDS` (if http)

### Provider C (MarketAux/FMP enrichment)
- `NEWS_PROVIDER_C_ENABLED`
- `NEWS_PROVIDER_C_NAME=MarketAux|FMP`
- `NEWS_PROVIDER_C_PROTOCOL=http`
- `NEWS_PROVIDER_C_URL`
- `NEWS_PROVIDER_C_API_KEY`
- `NEWS_PROVIDER_C_POLL_INTERVAL_SECONDS`

### Provider D (FRED context)
- `NEWS_PROVIDER_D_ENABLED`
- `NEWS_PROVIDER_D_NAME=FRED`
- `NEWS_PROVIDER_D_PROTOCOL=http`
- `NEWS_PROVIDER_D_URL`
- `NEWS_PROVIDER_D_API_KEY` (if needed for selected endpoints)
- `NEWS_PROVIDER_D_PULL_INTERVAL_SECONDS`

### Global reliability
- `NEWS_RECONNECT_BASE_SECONDS`
- `NEWS_RECONNECT_MAX_SECONDS`
- `NEWS_RECONNECT_JITTER_MS`
- `NEWS_MAX_RETRIES_BEFORE_FAILOVER`
- `NEWS_STALE_MESSAGE_THRESHOLD_SECONDS`
- `NEWS_FAILBACK_CHECK_INTERVAL_SECONDS`
- `NEWS_LOG_LEVEL`

---

## Done Criteria for 1.1
- [ ] A/B/C/D provider keys documented in `.env.example`
- [ ] Alert failover A→B implemented and tested
- [ ] Stream heartbeat/reconnect implemented where protocol is WS
- [ ] HTTP polling + idempotent cursor/time-window implemented where protocol is HTTP
- [ ] Unified normalized contracts emitted (event + enrichment + metadata)
- [ ] Health + structured logs expose full ingestion lifecycle
- [ ] 24h run test passes with auto recovery and no reconnect storm
- [ ] Clear note in docs: FRED is context/validation, not release-second trigger source