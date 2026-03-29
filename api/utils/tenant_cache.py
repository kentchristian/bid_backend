from django.core.cache import cache

def set_cache_key(api_name, tenant_id):
  return f"{api_name}:{tenant_id}"

def get_tenant_cache(cache_key):
  return cache.get(cache_key)
  
def set_tenant_cache(cache_key, data, timeout=60): # Default drop is at 60 seconds
  cache.set(cache_key, data, timeout=timeout)

