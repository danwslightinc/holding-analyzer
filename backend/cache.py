import time
from functools import wraps

class TTLCache:
    def __init__(self, ttl_seconds=300):
        self.ttl = ttl_seconds
        self.cache = {}

    def get(self, key):
        if key in self.cache:
            val, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return val
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear(self):
        self.cache = {}

# Global caches for different data types
prices_cache = TTLCache(ttl_seconds=60)      # Prices update every 1 min
fundamentals_cache = TTLCache(ttl_seconds=3600) # Fundamentals update every 1 hour
technicals_cache = TTLCache(ttl_seconds=1800)   # Technicals update every 30 mins
news_cache = TTLCache(ttl_seconds=600)         # News update every 10 mins
dividend_cache = TTLCache(ttl_seconds=3600)    # Dividends update every 1 hour
history_cache = TTLCache(ttl_seconds=3600)     # History update every 1 hour
fx_cache = TTLCache(ttl_seconds=300)          # FX update every 5 mins

def cache_result(cache_obj):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a key from arguments. For list of symbols, we sort them to ensure same key.
            key = str(args) + str(sorted(kwargs.items()))
            
            cached_val = cache_obj.get(key)
            if cached_val is not None:
                return cached_val
            
            result = func(*args, **kwargs)
            cache_obj.set(key, result)
            return result
        return wrapper
    return decorator
def clear_all_caches():
    prices_cache.clear()
    fundamentals_cache.clear()
    technicals_cache.clear()
    news_cache.clear()
    dividend_cache.clear()
    history_cache.clear()
    fx_cache.clear()
    print("All caches cleared")
