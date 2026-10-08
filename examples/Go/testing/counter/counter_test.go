package counter

import (
	"errors"
	"fmt"
	"testing"
)

func TestNew(t *testing.T) {
	c0 := New(0)
	c1 := New(1)
	if c0.Value() != 0 {
		t.Errorf("New(0).Value() = %d, want 0", c0.Value())
	}
	if c1.Value() != 1 {
		t.Errorf("New(1).Value() = %d, want 1", c1.Value())
	}
}

// Subtests, nested two levels deep.
func TestOperations(t *testing.T) {
	t.Run("Increment", func(t *testing.T) {
		c := New(1)
		if got := c.Increment(); got != 1 {
			t.Errorf("Increment() = %d, want 1", got)
		}
		if c.Value() != 2 {
			t.Errorf("Value() = %d, want 2", c.Value())
		}
	})

	t.Run("Decrement", func(t *testing.T) {
		c := New(1)
		if got, err := c.Decrement(); got != 1 || err != nil {
			t.Errorf("Decrement() = %d, %v, want 1, nil", got, err)
		}

		t.Run("Underflow", func(t *testing.T) {
			if _, err := c.Decrement(); !errors.Is(err, ErrUnderflow) {
				t.Errorf("Decrement() error = %v, want %v", err, ErrUnderflow)
			}
		})
	})
}

// Table-driven subtests: one per row.
func TestIncrementFrom(t *testing.T) {
	for _, start := range []int{0, 1, 41} {
		t.Run(fmt.Sprintf("start=%d", start), func(t *testing.T) {
			t.Logf("Incrementing from %d.", start)
			c := New(start)
			c.Increment()
			if c.Value() != start+1 {
				t.Errorf("Value() = %d, want %d", c.Value(), start+1)
			}
		})
	}
}

// Intended failure: Increment returns the value before incrementing.
func TestFailing(t *testing.T) {
	c := New(1)
	if got := c.Increment(); got != 2 {
		t.Errorf("Increment() = %d, want 2", got)
	}
}

// Intended skip.
func TestSkipped(t *testing.T) {
	t.Skip("Reset isn't tested yet.")
}

// An example is run as a test, too: its output is compared with the Output comment.
func ExampleCounter() {
	c := New(5)
	c.Increment()
	fmt.Println(c.Value())
	// Output: 6
}
