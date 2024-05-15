#include "Counter.hpp"

int Counter::Value() {
	return _value;
}

int Counter::Increment() {
	return _value++;
}

int Counter::Decrement() {
	return _value--;
}
