package internal

import (
	"sync"
	"time"
)

// DefaultTTL is used by all caches that don't set their own TTL.
var DefaultTTL = 30 * time.Second

// Cache is a concurrency-safe, lazy cache for typed command output.
// First call to Response() triggers the fetch. Subsequent calls return
// cached data unless the TTL has expired.
type Cache[T any] struct {
	mu       sync.Mutex
	Fn       func() T
	response T
	at       time.Time
	TTL      time.Duration
}

// Response returns cached data, refreshing first if stale or never fetched.
func (c *Cache[T]) Response() T {
	c.mu.Lock()
	defer c.mu.Unlock()

	ttl := c.TTL
	if ttl == 0 {
		ttl = DefaultTTL
	}

	if c.at.IsZero() || time.Since(c.at) >= ttl {
		c.response = c.Fn()
		c.at = time.Now()
	}

	return c.response
}
