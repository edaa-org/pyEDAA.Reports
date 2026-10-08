// A bounded stack in C++, which throws on overflow and underflow.
#pragma once

#include <stdexcept>

namespace Containers {
	class Stack {
		private:
			int _values[4];
			int _count = 0;

		public:
			void Push(int value) {
				if (_count == 4)
					throw std::overflow_error("Stack is full.");
				_values[_count++] = value;
			}

			int Pop() {
				if (_count == 0)
					throw std::underflow_error("Stack is empty.");
				return _values[--_count];
			}

			bool IsEmpty() const {
				return _count == 0;
			}
	};
}
