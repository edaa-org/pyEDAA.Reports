package my.pack;

import static org.junit.Assert.*;

import org.junit.Test;

public class OtherClassTest {

	@Test
	public void testReturnThree() {
		System.out.println("Output on STDOUT.");
		System.err.println("Output on STDERR.");
		assertEquals(3, new OtherClass().returnThree());
	}

}
