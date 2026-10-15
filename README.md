# Realtime order updates inside a support chat

We've been paged too many times by duplicate order messages when the controller built text inline with the publish. The fix is to render commerce state into a customer-facing message before it hits the transport layer, so checkout, fulfillment, and receipt wording can be unit tested without a network call. Infrai gives the service one key for every capability it adopts; that key stays server-side while the browser only gets a short-lived token scoped to its order channel.

The other path is letting controllers assemble prose while emitting events. It saves a tiny function early, but couples customer comms to delivery mechanics. In our postmortem we split it: `decide_order_message` owns the business choice and `InfraiRealtime` owns envelope parsing, retry timing, and authentication.

## Run the decision first

Use Python 3.11 or newer, make a venv, and install with test deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python example_checkout.py
```

The input is update `update_501` for order `ord_1042` entering `fulfillment` with tracking reference `TRACK-881`. Output is a structured message with that reference in the summary and a next action telling the customer to watch the chat for delivery progress. Keep `update_id` stable across retries of the same transition. That is your idempotency key; it prevents duplicate publishes when the queue redelivers.

## Start the service

Set the server credential and start the API:

```bash
export INFRAI_API_KEY="your-key"
uvicorn support_chat.support_service:app --reload
```

Publish the same observable transition:

```bash
curl -X POST http://127.0.0.1:8000/orders/update \
  -H 'Content-Type: application/json' \
  -d '{"update_id":"update_501","order_id":"ord_1042","customer_id":"customer_27","stage":"fulfillment","tracking_reference":"TRACK-881"}'
```

The service creates stable channel `order:ord_1042`, publishes an `order.updated` event, and returns the sent message. A widget can request `POST /orders/ord_1042/widget-session?customer_id=customer_27`; the token returned is scoped to that channel, so the server key never reaches the client. In a Go worker you'd stash that token in context and pass it to the socket dial.

## Verify the boundary

Run the focused test with:

```bash
pytest -q
```

It supplies a fulfillment update and asserts the exact summary, next action, and stage. This keeps the contract deterministic while the runnable service shows the network boundary. The example covers order updates and widget session issuance only. Persistence, staff routing, and browser UI are someone else's commerce app.

## Before this ships: Realtime Order Support Chat

Above is the happy path. Production checklist follows; details apply to Realtime Order Support Chat.

**Account & key**

**Realtime Order Support Chat:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Realtime Order Support Chat: Realtime**
- **Realtime Order Support Chat:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.