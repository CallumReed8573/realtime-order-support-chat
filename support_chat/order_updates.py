from typing import Literal

from pydantic import BaseModel, Field


OrderStage = Literal["checkout", "fulfillment", "receipt"]


class OrderUpdateRequest(BaseModel):
    update_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    stage: OrderStage
    tracking_reference: str | None = None
    receipt_reference: str | None = None


class OrderMessage(BaseModel):
    order_id: str
    stage: OrderStage
    summary: str
    next_action: str


def decide_order_message(update: OrderUpdateRequest) -> OrderMessage:
    """Turn commerce state into the one update a shopper needs now."""
    if update.stage == "checkout":
        return OrderMessage(
            order_id=update.order_id,
            stage=update.stage,
            summary="Checkout received",
            next_action="We will post another update when fulfillment begins.",
        )
    if update.stage == "fulfillment":
        detail = (
            f" Tracking reference: {update.tracking_reference}."
            if update.tracking_reference
            else ""
        )
        return OrderMessage(
            order_id=update.order_id,
            stage=update.stage,
            summary=f"Your order is being fulfilled.{detail}",
            next_action="Watch this chat for delivery progress.",
        )
    detail = (
        f" Receipt reference: {update.receipt_reference}."
        if update.receipt_reference
        else ""
    )
    return OrderMessage(
        order_id=update.order_id,
        stage=update.stage,
        summary=f"Your receipt is ready.{detail}",
        next_action="Keep the receipt reference for returns or support.",
    )
