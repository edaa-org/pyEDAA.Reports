#include "Counter.hpp"

#include <climits>
#include <stdexcept>

Counter::Counter(int value) : _value { value } {}

int Counter::Value() {
	return _value;
}

int Counter::Increment() {
	if (_value == INT_MAX) {
		throw std::overflow_error("Counter overflow.");
	}
	return _value++;
}

int Counter::Decrement() {
	if (_value == 0) {
		throw std::underflow_error("Counter underflow.");
	}
	return _value--;
}

void Counter::Reset() {
	_value = 0;
}
