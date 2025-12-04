def get_sale_percent(price_without_discount: int, price_with_discount: int) -> str:
    """Получаем скидку на товар в процентах."""

    if (
        price_with_discount == price_without_discount
        or price_without_discount < price_with_discount
        or price_without_discount is None
        or price_with_discount is None
    ):
        return "Скидка 0%"
    difference = price_without_discount - price_with_discount
    discount_percent = round(difference / price_without_discount * 100)

    return f"Скидка {discount_percent}%"
