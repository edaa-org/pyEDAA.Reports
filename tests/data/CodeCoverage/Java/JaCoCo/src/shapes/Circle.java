package shapes;

import java.util.function.DoubleUnaryOperator;

public class Circle implements Shape {
	private final double radius;

	public Circle(double radius) {
		if (radius < 0.0) {
			throw new IllegalArgumentException("Negative radius.");
		}
		this.radius = radius;
	}

	@Override
	public double area() {
		DoubleUnaryOperator square = value -> value * value;
		return Math.PI * square.applyAsDouble(radius);
	}

	public static class Unit {
		public static double toMillimeters(double meters) {
			return meters * 1000.0;
		}
	}
}
