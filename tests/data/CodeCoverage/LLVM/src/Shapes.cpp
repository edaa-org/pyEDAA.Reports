#include "Statistics.h"

namespace Geometry {
	template <typename T>
	T Max(T first, T second) {
		return first > second ? first : second;
	}

	class Rectangle {
		public:
			Rectangle(int width, int height) : _width(width), _height(height) {}

			int Area() const {
				return _width * _height;
			}

			bool IsSquare() const {
				return _width == _height;
			}

		private:
			int _width;
			int _height;
	};
}

int main() {
	const int values[] = {1, 2, 3};
	Geometry::Rectangle rectangle(2, 3);

	int result = SumOfSquares(values, 3) + Clamp(15, 0, 10) + Clamp(-5, 0, 10);
	result += InRange(5, 0, 10, 0) + InRange(10, 0, 10, 1);
	result += Average(result, 2) + rectangle.Area();
	result += Geometry::Max(1, 2) + (int)Geometry::Max(1.5, 0.5);
	if (rectangle.IsSquare()) {
		result = 0;
	}

	return result > 0 ? 0 : 1;
}
