from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance - imported by main.py (to attach to app.state and
# register the exception handler/middleware) and by individual route
# modules (to apply per-endpoint limits via @limiter.limit(...)).
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
