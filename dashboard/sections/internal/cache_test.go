package internal

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestResponseTriggersFirstFetch(t *testing.T) {
	calls := 0
	c := Cache[string]{Fn: func() string {
		calls++
		return "hello"
	}}

	assert.Equal(t, "hello", c.Response())
	assert.Equal(t, 1, calls)
}

func TestResponseReturnsCachedWithinTTL(t *testing.T) {
	calls := 0
	c := Cache[int]{Fn: func() int {
		calls++
		return calls
	}, TTL: time.Minute}

	first := c.Response()
	second := c.Response()

	assert.Equal(t, first, second)
	assert.Equal(t, 1, calls)
}

func TestResponseRefreshesAfterTTL(t *testing.T) {
	calls := 0
	c := Cache[int]{Fn: func() int {
		calls++
		return calls
	}, TTL: time.Millisecond}

	first := c.Response()
	time.Sleep(2 * time.Millisecond)
	second := c.Response()

	assert.NotEqual(t, first, second)
	assert.Equal(t, 2, calls)
}

func TestResponseUsesDefaultTTL(t *testing.T) {
	original := DefaultTTL
	defer func() { DefaultTTL = original }()

	DefaultTTL = time.Millisecond

	calls := 0
	c := Cache[int]{Fn: func() int {
		calls++
		return calls
	}}

	c.Response()
	time.Sleep(2 * time.Millisecond)
	c.Response()

	assert.Equal(t, 2, calls)
}
