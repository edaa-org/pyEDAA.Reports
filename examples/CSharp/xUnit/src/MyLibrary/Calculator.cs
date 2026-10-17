namespace MyLibrary;

public class Calculator
{
	public int Add(int augend, int addend) => augend + addend;

	public int Divide(int dividend, int divisor) => dividend / divisor;

	public int Absolute(int value)
	{
		if (value < 0)
		{
			return -value;
		}

		return value;
	}

	// Intended bug: checks for odd values.
	public bool IsEven(int value) => value % 2 == 1;

	public int SumOfPositives(IEnumerable<int> values) => values.Where(value => value > 0).Sum();
}
