package stack

import "testing"

// Table-driven subtests with a failing row (intended failure: the stack doesn't sort).
func TestPushPop(t *testing.T) {
	tests := []struct {
		name  string
		items []int
		want  int
	}{
		{"one item", []int{1}, 1},
		{"two items", []int{1, 2}, 2},
		{"sorted", []int{3, 1, 2}, 3},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var s Stack
			for _, item := range test.items {
				s.Push(item)
			}
			if got := s.Pop(); got != test.want {
				t.Errorf("Pop() = %d, want %d", got, test.want)
			}
		})
	}
}

func TestLen(t *testing.T) {
	var s Stack
	s.Push(1)
	s.Push(2)
	if s.Len() != 2 {
		t.Errorf("Len() = %d, want 2", s.Len())
	}
}

// Intended error: Pop panics on an empty stack. The panic ends the package's test binary, so this is the last test.
func TestPopEmpty(t *testing.T) {
	var s Stack
	s.Pop()
}
