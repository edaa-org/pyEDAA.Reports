#include "Counter.hpp"

#include <stdexcept>

#include <catch2/catch_test_macros.hpp>

TEST_CASE("Init", "[Counter]") {
	Counter c0 { 0 };
	Counter c1 { 1 };
	CHECK(c0.Value() == 0);
	CHECK(c1.Value() == 1);
}

TEST_CASE("Operations", "[Counter]") {
	Counter c { 1 };

	SECTION("Increment") {
		CHECK(c.Increment() == 1);
		CHECK(c.Value() == 2);
	}

	SECTION("Decrement") {
		CHECK(c.Decrement() == 1);
		CHECK(c.Value() == 0);

		SECTION("Underflow") {
			CHECK_THROWS_AS(c.Decrement(), std::underflow_error);
		}
	}
}

class CounterFixture {
	protected:
		Counter _counter { 5 };
};

TEST_CASE_METHOD(CounterFixture, "Fixture", "[Counter]") {
	CHECK(_counter.Increment() == 5);
	CHECK(_counter.Value() == 6);
}

// Intended failure: Increment returns the value before incrementing.
TEST_CASE("Failing", "[Counter]") {
	Counter c { 1 };
	CHECK(c.Increment() == 2);
}

// Intended skip.
TEST_CASE("Skipped", "[Counter]") {
	SKIP("Reset isn't tested yet.");
}

// Intended error: an exception escapes the test case.
TEST_CASE("Exception", "[Counter]") {
	Counter c { 0 };
	c.Decrement();
}
