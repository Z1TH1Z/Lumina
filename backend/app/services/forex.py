import httpx
import json
import logging
from app.core.config import get_settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Fallback rates in case API fails or key is invalid
FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.00,
    "JPY": 150.00,
    "CAD": 1.35,
    "AUD": 1.52,
    "CHF": 0.88,
    "CNY": 7.20
}

async def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)

async def fetch_latest_rates(base_currency: str = "USD") -> dict:
    """
    Fetches the latest exchange rates from ExchangeRate-API.
    Caches the result in Redis for 12 hours to avoid rate limits.
    """
    settings = get_settings()
    api_key = settings.EXCHANGERATE_API_KEY
    redis = await get_redis_client()
    cache_key = f"forex_rates_{base_currency}"

    # Check cache first
    try:
        cached_data = await redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        logger.error(f"Redis cache error: {e}")

    # Fetch from API
    rates = FALLBACK_RATES.copy()
    if api_key:
        try:
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("result") == "success":
                        rates = data.get("conversion_rates", rates)
                        # Cache for 12 hours (43200 seconds)
                        await redis.setex(cache_key, 43200, json.dumps(rates))
        except Exception as e:
            logger.error(f"Failed to fetch from ExchangeRate-API: {e}")

    return rates

async def convert_currency(amount: float, from_curr: str, to_curr: str) -> float:
    """
    Converts an amount from one currency to another using the latest rates.
    """
    if from_curr == to_curr:
        return amount

    # We fetch rates based on USD as the base to do cross-conversions
    rates = await fetch_latest_rates(base_currency="USD")
    
    # from_curr to USD, then USD to to_curr
    rate_from = rates.get(from_curr, FALLBACK_RATES.get(from_curr, 1.0))
    rate_to = rates.get(to_curr, FALLBACK_RATES.get(to_curr, 1.0))

    # Convert to USD first
    amount_in_usd = amount / rate_from
    # Convert USD to target currency
    final_amount = amount_in_usd * rate_to
    
    return final_amount
