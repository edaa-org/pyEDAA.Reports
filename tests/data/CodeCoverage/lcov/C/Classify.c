/* Exercised partly, so the report has covered, missed and partially covered lines, branches and functions. */
#include <stdio.h>
#include "Clamp.h"

static int Sign(int value) {
	if (value < 0)
		return -1;
	else if (value > 0)
		return 1;
	return 0;
}

static int InRange(int value, int low, int high) {
	return value >= low && value <= high;
}

static int Twice(int value) {
	if (value < 0)
		return 0;
	return 2 * value;
}

int main(void) {
	int sum = 0;
	for (int i = 1; i <= 3; ++i) {
		sum += Sign(i);
		if (InRange(i, 2, 5))
			sum += Clamp(i, 0, 2);
	}

	printf("%d\n", sum);
	return 0;
}
