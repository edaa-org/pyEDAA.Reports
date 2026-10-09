#ifndef STATISTICS_H
#define STATISTICS_H

#ifdef __cplusplus
extern "C" {
#endif

int SumOfSquares(const int* values, int count);
int Clamp(int value, int low, int high);
int InRange(int value, int low, int high, int inclusive);
int Negate(int value);

static inline int Average(int sum, int count) {
	return count == 0 ? 0 : sum / count;
}

#ifdef __cplusplus
}
#endif

#endif
