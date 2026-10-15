from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from fastapi import FastAPI, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse

from .infrai_realtime import InfraiError, InfraiRealtime
from .order_updates import OrderMessage, OrderUpdateRequest, decide_order_message


class PublishedUpdate(BaseModel):
    channel: str
    message: OrderMessage


class WidgetSession(BaseModel):
    channel: str
    token: dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    realtime = InfraiRealtime.from_environment()
    app.state.realtime = realtime
    yield
    await realtime.close()


app = FastAPI(title="Order support chat", lifespan=lifespan)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_: Request, exc: InfraiError) -> JSONResponse:
    status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "code": exc.code,
                "message": "The realtime request was rejected.",
            }
        },
    )


@app.post("/orders/update", response_model=PublishedUpdate)
async def publish_update(update: OrderUpdateRequest, request: Request) -> PublishedUpdate:
    message = decide_order_message(update)
    channel = f"order:{update.order_id}"
    realtime: InfraiRealtime = request.app.state.realtime
    await realtime.create_channel(channel)
    await realtime.publish_order_update(
        channel=channel,
        event="order.updated",
        data=message.model_dump(),
        account_id=update.customer_id,
        event_id=f"order-update:{update.update_id}",
    )
    return PublishedUpdate(channel=channel, message=message)


@app.post("/orders/{order_id}/widget-session", response_model=WidgetSession)
async def create_widget_session(
    order_id: str,
    customer_id: str,
    request: Request,
) -> WidgetSession:
    channel = f"order:{order_id}"
    realtime: InfraiRealtime = request.app.state.realtime
    await realtime.create_channel(channel)
    token = await realtime.issue_widget_token(customer_id, channel)
    return WidgetSession(channel=channel, token=token)
