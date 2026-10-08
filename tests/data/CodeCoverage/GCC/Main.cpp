// Exercise the stack partly: an underflow is caught, an overflow never happens.
#include <iostream>
#include <stdexcept>

#include "Containers/Stack.hpp"

template <typename T>
T Maximum(T a, T b) {
	return (a > b) ? a : b;
}

int Drain(Containers::Stack& stack) {
	int sum = 0;
	try {
		while (true)
			sum += stack.Pop();
	} catch (const std::underflow_error&) {
		std::cout << "drained" << std::endl;
	}
	return sum;
}

int main() {
	Containers::Stack stack;
	stack.Push(1);
	stack.Push(2);
	std::cout << Drain(stack) << std::endl;
	std::cout << Maximum(3, 5) << " " << Maximum(2.5, 1.5) << std::endl;
	return stack.IsEmpty() ? 0 : 1;
}
