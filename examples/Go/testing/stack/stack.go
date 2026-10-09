// Package stack provides a stack of integers.
package stack

// Stack is a last-in, first-out stack of integers.
type Stack struct {
	items []int
}

// Push puts an item on top of the stack.
func (s *Stack) Push(item int) {
	s.items = append(s.items, item)
}

// Pop removes the item on top of the stack and returns it. It panics on an empty stack.
func (s *Stack) Pop() int {
	last := len(s.items) - 1
	item := s.items[last]
	s.items = s.items[:last]
	return item
}

// Len returns the number of items on the stack.
func (s *Stack) Len() int {
	return len(s.items)
}
