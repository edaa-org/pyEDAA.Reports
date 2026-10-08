using Xunit;

namespace MyLibrary.Tests;

public class CounterTests(ITestOutputHelper output)
{
	[Fact]
	public void Increment()
	{
		var counter = new Counter();
		counter.Increment();
		output.WriteLine($"Counter value: {counter.Value}");

		Assert.Equal(1, counter.Value);
	}

	[Fact]
	public void Decrement()
	{
		var counter = new Counter();
		counter.Increment();
		counter.Decrement();

		Assert.Equal(0, counter.Value);
	}

	[Fact]
	public async Task IncrementAsync() => Assert.Equal(1, await new Counter().IncrementAsync());
}
