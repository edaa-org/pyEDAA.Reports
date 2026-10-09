package shapes;

public interface Shape {
	double area();

	default String describe() {
		return getClass().getSimpleName() + " of area " + area();
	}
}
