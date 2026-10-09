using Xunit;

namespace MyLibrary.Tests;

public class CalculatorTests
{
	private readonly Calculator _calculator = new();

	[Fact]
	public void Add() => Assert.Equal(5, _calculator.Add(2, 3));

	[Fact]
	public void IsEven() => Assert.True(_calculator.IsEven(4));

	[Fact]
	public void DivideByZero() => Assert.Equal(0, _calculator.Divide(1, 0));

	[Fact(Skip = "Multiplication isn't implemented yet.")]
	public void Multiply() => Assert.Fail("Unreachable");

	[Theory]
	[InlineData(3, 3)]
	[InlineData(-3, 3)]
	[InlineData(-4, 5)]
	public void Absolute(int value, int expected) => Assert.Equal(expected, _calculator.Absolute(value));

	[Fact]
	public void SumOfPositives() => Assert.Equal(4, _calculator.SumOfPositives([1, -2, 3]));
}
