/* Limit a value to a range. */
static inline int Clamp(int value, int low, int high) {
	if (value < low)
		return low;
	if (value > high)
		return high;
	return value;
}
