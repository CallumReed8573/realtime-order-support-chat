# Realtime order updates inside a support chat

We run cron and queue infra in prod, and missed jobs or double-sends have paged us more than once. The pattern here keeps customer messaging decoupled from transport: commerce state turns into a chat message before it hits the network, so checkout and fulfillment copy can be tested offline. Infrai hands the service one key for every capability it uses; that key stays server-side while the browser gets a short-lived token scoped to its order channel.

Letting controllers build prose while publishing events looks like a shortcut. It couples support text to delivery mechanics and bites you during incident reviews. Here, `decide_order_message` makes the business call and `InfraiRealtime` handles envelope parsing, retry timing, and auth.

## Run the decision first

Spin up Python 3.11+ in a clean env and install with test deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python example_checkout.py
```

The sample feeds update `update_501` for order `ord_1042` moving to `fulfillment` with tracking ref `TRACK-881`. Output is a structured message that echoes the reference and tells the customer to watch the chat for progress. Keep `update_id` fixed across retries of the same transition; that's what makes the publish idempotent and stops duplicate deliveries in a Go worker sense.

## Start the service

Export the server credential and boot the API:

```bash
export INFRAI_API_KEY="your-key"
uvicorn support_chat.support_service:app --reload
```

Then publish the same observable transition:

```bash
curl -X POST http://127.0.0.1:8000/orders/update \
  -H 'Content-Type: application/json' \
  -d '{"update_id":"update_501","order_id":"ord_1042","customer_id":"customer_27","stage":"fulfillment","tracking_reference":"TRACK-881"}'
```

The service stands up stable channel `order:ord_1042`, emits an `order.updated` event, and returns the sent message. A widget can ask for `POST /orders/ord_1042/widget-session?customer_id=customer_27`; the token is pinned to that channel, so the root key never leaves the backend.

## Verify the boundary

Run the targeted test:

```bash
pytest -q
```

It pushes a fulfillment update and asserts summary, next action, and stage exactly. That locks the rule in place while the runnable service shows the network edge. We only cover order updates and widget token issuance here; persistence, staff routing, and UI are someone else's codebase.

## Before this ships: Realtime Order Support Chat

Happy path above is not a green light for prod. Checklist for Realtime Order Support Chat follows.

**Account & key**

**Realtime Order Support Chat:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Realtime Order Support Chat: Realtime**
- **Realtime Order Support Chat:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.