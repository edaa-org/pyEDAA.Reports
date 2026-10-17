package util;

public final class Numbers {
	private Numbers() {
	}

	public static int clamp(int value, int low, int high) {
		if (value < low) {
			return low;
		} else if (value > high) {
			return high;
		}
		return value;
	}
}
