package my.pack;

import static org.junit.Assert.*;
import static org.junit.Assume.*;

import org.junit.Ignore;
import org.junit.Test;

public class MyClassTest {

	@Test
	public void testReturnTrue() {
		assertTrue("returnTrue() returned false.", new MyClass().returnTrue());
	}

	@Test
	public void testReturnFalse() {
		assertFalse(new MyClass().returnFalse());
	}

	@Test
	public void testAbsolute() {
		assertEquals(5, new MyClass().absolute(5));
	}

	@Test
	public void testDivideByZero() {
		assertEquals(0, new MyClass().divide(1, 0));
	}

	@Test
	@Ignore("Ignored by intention.")
	public void testIgnored() {
		fail("An ignored test isn't executed.");
	}

	@Test
	public void testAssumption() {
		assumeTrue("Skipped by a failed assumption.", false);
	}

}
