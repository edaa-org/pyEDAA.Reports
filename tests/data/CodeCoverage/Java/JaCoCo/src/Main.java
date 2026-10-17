import shapes.Circle;
import util.Numbers;

public class Main {
	public static void main(String[] arguments) {
		Circle circle = new Circle(2.0);
		System.out.println(circle.describe());
		System.out.println(Numbers.clamp(5, 0, 3));
	}

	static void unused() {
		System.out.println("Never called.");
	}
}
