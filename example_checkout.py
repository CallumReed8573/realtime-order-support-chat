import asyncio

from support_chat.order_updates import OrderUpdateRequest, decide_order_message


async def main() -> None:
    update = OrderUpdateRequest(
        update_id="update_501",
        order_id="ord_1042",
        customer_id="customer_27",
        stage="fulfillment",
        tracking_reference="TRACK-881",
    )
    message = decide_order_message(update)
    print(message.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
