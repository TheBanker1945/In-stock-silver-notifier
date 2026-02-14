# LEGACY: Kept as fallback. Primary deal evaluation is now handled by SilverStack dashboard.
import config


def is_good_deal(price_per_oz: float, spot_price_per_oz: float, total_price: float) -> bool:
    """Determine if a product price qualifies as a buy.

    A product is a deal ONLY if BOTH conditions are met:
      1. price_per_oz <= spot_price_per_oz + MAX_PREMIUM
      2. total_price <= HARD_CAP
    """
    within_premium = price_per_oz <= (spot_price_per_oz + config.MAX_PREMIUM)
    under_cap = total_price <= config.HARD_CAP
    return within_premium and under_cap
