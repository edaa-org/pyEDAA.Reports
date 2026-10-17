// Package counter provides a counter, which can't count below zero.
package counter

import "errors"

// ErrUnderflow is returned when a counter at zero is decremented.
var ErrUnderflow = errors.New("counter: underflow")

// Counter counts up and down, but not below zero.
type Counter struct {
	value int
}

// New returns a counter starting at value.
func New(value int) *Counter {
	return &Counter{value: value}
}

// Value returns the counter's current value.
func (c *Counter) Value() int {
	return c.value
}

// Increment increments the counter and returns the value before incrementing.
func (c *Counter) Increment() int {
	old := c.value
	c.value++

	// The value before incrementing.
	return old
}

// Decrement decrements the counter and returns the value before decrementing.
func (c *Counter) Decrement() (int, error) {
	if c.value == 0 {
		return 0, ErrUnderflow
	}
	old := c.value
	c.value--
	return old, nil
}

// Reset sets the counter back to zero.
func (c *Counter) Reset() {
	c.value = 0
}
