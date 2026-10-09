namespace MyLibrary;

public class Counter
{
	public int Value { get; private set; }

	public void Increment() => Value++;

	public void Decrement()
	{
		if (Value == 0)
		{
			throw new InvalidOperationException("Counter is already zero.");
		}

		Value--;
	}

	public async Task<int> IncrementAsync()
	{
		await Task.Yield();
		Increment();
		return Value;
	}

	public void Reset() => Value = 0;
}
