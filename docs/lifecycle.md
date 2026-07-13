# Ingestion Supervisor State Model & Lifecycle Flow (1.1.3.f)

## State model

The ingestion runtime uses the following states:

- `idle`  
  Supervisor is instantiated but not running.

- `connecting`  
  Supervisor is establishing provider session/connection.

- `connected`  
  Provider connection is healthy and messages are being consumed.

- `degraded`  
  Runtime is partially functional (e.g., provider is connected but dispatch is failing).

- `reconnecting`  
  Runtime encountered a provider/runtime failure and is attempting recovery.

- `stopped`  
  Supervisor has been intentionally stopped and resources are closed.

### Allowed transitions

- `idle -> connecting` (on `start`)
- `connecting -> connected` (on successful connect)
- `connecting -> reconnecting` (connect failure)
- `connected -> degraded` (dispatch failure/non-fatal downstream issue)
- `connected -> reconnecting` (stream/provider failure)
- `degraded -> connected` (dispatch recovers)
- `degraded -> reconnecting` (provider/session failure while degraded)
- `reconnecting -> connecting` (retry attempt begins)
- `reconnecting -> connected` (recovery successful)
- `reconnecting -> stopped` (stop requested during recovery)
- `* -> stopped` (on `stop`)

---

## Main lifecycle flow

High-level runtime flow:

1. **init**
   - load `IngestionSettings`
   - resolve active provider (A/B)
   - initialize dispatcher + health counters

2. **connect**
   - transition to `connecting`
   - open provider connection/session
   - transition to `connected` on success

3. **receive**
   - consume provider stream (`listen`)
   - wrap each payload into `RawIngestionEvent`
   - update `last_message_at` when events are received

4. **dispatch**
   - send event to `MessageDispatcher`
   - if dispatch succeeds: remain/return `connected`
   - if dispatch fails: transition to `degraded` (non-fatal path)

5. **recover**
   - on provider/runtime exception: transition to `reconnecting`
   - increment reconnect counter
   - attempt failover hook (A -> B) when eligible
   - retry connect loop with backoff/sleep
   - transition back to `connected` when healthy

---

## Failure-handling notes

- Dispatch failure is treated as **degraded**, not immediate hard-stop.
- Provider stream/connect failures enter **reconnecting** path.
- Failover is a hook-based strategy and may be no-op if no alternate provider is available.
- `stop()` is authoritative and should force transition to `stopped` from any state.

---

## Health snapshot fields

Supervisor health should expose at least:

- `state`
- `active_provider`
- `last_message_at` (UTC ISO-8601)
- `reconnect_count`
- `failover_count`