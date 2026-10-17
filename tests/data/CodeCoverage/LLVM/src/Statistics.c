#include "Statistics.h"

#define CLAMP(value, low, high) ((value) < (low) ? (low) : ((value) > (high) ? (high) : (value)))
#define VERBOSE 0

static int Square(int value) {
	return value * value;
}

int SumOfSquares(const int* values, int count) {
	int sum = 0;
	for (int i = 0; i < count; i++) {
		sum += Square(values[i]);
	}

	return sum;
}

int Clamp(int value, int low, int high) {
	return CLAMP(value, low, high);
}

int InRange(int value, int low, int high, int inclusive) {
	if ((value > low && value < high) || (inclusive && (value == low || value == high))) {
		return 1;
	}

#if VERBOSE
	printf("out of range\n");
#endif
	return 0;
}

int Negate(int value) {
	return -value;
}
