import config


def is_good_deal(product_price: float, spot_price_per_oz: float) -> bool:
    """Determine if a product price qualifies as a buy.

    A product is a deal ONLY if BOTH conditions are met:
      1. product_price <= spot_price_per_oz + MAX_PREMIUM
      2. product_price <= HARD_CAP
    """
    within_premium = product_price <= (spot_price_per_oz + config.MAX_PREMIUM)
    under_cap = product_price <= config.HARD_CAP
    return within_premium and under_cap
