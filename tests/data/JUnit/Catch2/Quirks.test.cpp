// Catch2 v3 test cases showing how the JUnit reporter writes special cases. The report catch2-junit-quirks.xml is
// written by:
//   quirks --order decl --reporter JUnit::out=catch2-junit-quirks.xml
#include <iostream>

#include <catch2/catch_test_macros.hpp>

// No assertions: the test case is missing in the report.
TEST_CASE("NoAssertions", "[Quirks]") {
}

// No assertions, but output: the test case is reported, with its output.
TEST_CASE("Output", "[Quirks]") {
	std::cout << "Hello Catch2" << std::endl;
}

// An expected failure: <skipped> followed by <failure>.
TEST_CASE("MayFail", "[Quirks][!mayfail]") {
	CHECK(1 == 2);
}

// An unexpected pass: Catch2 counts the test case as failed, the report as passed.
TEST_CASE("ShouldFail", "[Quirks][!shouldfail]") {
	CHECK(1 == 1);
}

// A failure in a section: only the section's test case has a <failure>.
TEST_CASE("Nested", "[Quirks]") {
	CHECK(true);

	SECTION("Inner") {
		CHECK(1 == 2);
	}
}

// An explicit failure has no expression: <failure> without a message attribute.
TEST_CASE("ExplicitFailure", "[Quirks]") {
	FAIL("Explicit failure.");
}

// Two failed assertions: only the first is reported.
TEST_CASE("TwoFailures", "[Quirks]") {
	CHECK(1 == 2);
	CHECK(3 == 4);
}

namespace Namespace {
	class Fixture {
		protected:
			int _value { 1 };
	};
}

// A fixture class in a namespace: '::' becomes '.' in the classname.
TEST_CASE_METHOD(Namespace::Fixture, "NamespacedFixture", "[Quirks]") {
	CHECK(_value == 1);
}
