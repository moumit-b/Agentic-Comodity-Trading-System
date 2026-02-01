"""MCP Cache - Multi-level caching for performance optimization."""

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import hashlib
import json
from collections import OrderedDict


class MCPCache:
    """
    Multi-level cache for MCP results.
    Implements intelligent caching to improve response times.
    """

    def __init__(self, max_size: int = 1000, default_ttl_seconds: int = 3600):
        """
        Initialize the MCP cache.

        Args:
            max_size: Maximum number of entries in cache (LRU eviction)
            default_ttl_seconds: Default time-to-live for cache entries
        """
        self.max_size = max_size
        self.default_ttl = timedelta(seconds=default_ttl_seconds)

        # Cache storage: key -> (value, timestamp, ttl)
        self._cache: OrderedDict[str, tuple[Any, datetime, timedelta]] = OrderedDict()

        # Cache statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _generate_key(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate a cache key from MCP call parameters."""
        # Create deterministic string representation
        key_data = {
            "mcp": mcp_name,
            "tool": tool_name,
            "args": arguments,
        }
        key_string = json.dumps(key_data, sort_keys=True)

        # Hash for compact storage
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self,
        mcp_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and is not expired.

        Args:
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Cached value if found and valid, None otherwise
        """
        key = self._generate_key(mcp_name, tool_name, arguments)

        if key in self._cache:
            value, timestamp, ttl = self._cache[key]

            # Check if expired
            if datetime.now() - timestamp < ttl:
                # Move to end (LRU - mark as recently used)
                self._cache.move_to_end(key)
                self.hits += 1
                return value
            else:
                # Expired - remove from cache
                del self._cache[key]

        self.misses += 1
        return None

    def set(
        self,
        mcp_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        value: Any,
        ttl: Optional[timedelta] = None,
    ):
        """
        Store a value in the cache.

        Args:
            mcp_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments
            value: Value to cache
            ttl: Time-to-live for this entry (uses default if None)
        """
        key = self._generate_key(mcp_name, tool_name, arguments)
        ttl = ttl or self.default_ttl

        # Add to cache
        self._cache[key] = (value, datetime.now(), ttl)

        # Move to end (most recently added)
        self._cache.move_to_end(key)

        # Evict oldest if over max size
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)  # Remove oldest (FIFO)
            self.evictions += 1

    def invalidate(
        self,
        mcp_name: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        """
        Invalidate cache entries matching criteria.

        Args:
            mcp_name: If provided, invalidate only entries for this MCP
            tool_name: If provided, invalidate only entries for this tool
        """
        if mcp_name is None and tool_name is None:
            # Clear all
            self._cache.clear()
            return

        # Filter and remove matching entries
        keys_to_remove = []
        for key in self._cache.keys():
            # Would need to reverse the hash to check - for now, clear all if specific invalidation needed
            # In production, might store reverse mapping
            pass

        # Simplified: if specific invalidation needed, clear all for now
        # TODO: Implement reverse mapping for selective invalidation
        if mcp_name or tool_name:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions,
        }

    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup_expired(self):
        """Remove all expired entries from cache."""
        now = datetime.now()
        keys_to_remove = []

        for key, (value, timestamp, ttl) in self._cache.items():
            if now - timestamp >= ttl:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        return len(keys_to_remove)
