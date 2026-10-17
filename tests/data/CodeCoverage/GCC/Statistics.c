/* Integer statistics in C, exercised partly by main(). */
#include <stdio.h>

static int Clamp(int value, int low, int high) {
	if (value < low)
		return low;
	else if (value > high)
		return high;
	return value;
}

int Sum(const int* values, int count) {
	int sum = 0;
	for (int i = 0; i < count; ++i)
		sum += values[i];
	return sum;
}

int InRange(int value, int low, int high) {
	return value >= low && value <= high;
}

int Twice(int value) {
	return value * 2;
}

int main(void) {
	int values[] = {3, 7, 11};
	printf("%d\n", Sum(values, 3));
	printf("%d\n", Clamp(15, 0, 10));
	printf("%d\n", InRange(5, 0, 10));
	return 0;
}
