from support_chat.order_updates import OrderUpdateRequest, decide_order_message


def test_fulfillment_update_includes_tracking_and_next_action() -> None:
    update = OrderUpdateRequest(
        update_id="update_501",
        order_id="ord_1042",
        customer_id="customer_27",
        stage="fulfillment",
        tracking_reference="TRACK-881",
    )

    message = decide_order_message(update)

    assert message.summary == "Your order is being fulfilled. Tracking reference: TRACK-881."
    assert message.next_action == "Watch this chat for delivery progress."
    assert message.stage == "fulfillment"
