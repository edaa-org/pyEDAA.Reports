package my.pack;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assumptions.*;

import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestReporter;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

@DisplayName("Tests of MyClass")
class MyClassTest {

	@Test
	void testReturnTrue() {
		assertTrue(new MyClass().returnTrue(), "returnTrue() returned false.");
	}

	@Test
	@Tag("fast")
	@DisplayName("returnFalse() returns false")
	void testReturnFalse() {
		assertFalse(new MyClass().returnFalse());
	}

	@Test
	void testDivideByZero() {
		assertEquals(0, new MyClass().divide(1, 0));
	}

	@Test
	@Disabled("Disabled by intention.")
	void testDisabled() {
		fail("A disabled test isn't executed.");
	}

	@Test
	void testAssumption() {
		assumeTrue(false, "Aborted by a failed assumption.");
	}

	@ParameterizedTest
	@CsvSource({"5, 5", "-5, 5", "0, 1"})
	void testAbsolute(int value, int expected, TestReporter reporter) {
		reporter.publishEntry("value", String.valueOf(value));
		assertEquals(expected, new MyClass().absolute(value));
	}

	@Nested
	class Divide {
		@Test
		void testDivide() {
			assertEquals(2, new MyClass().divide(4, 2));
		}
	}

}
