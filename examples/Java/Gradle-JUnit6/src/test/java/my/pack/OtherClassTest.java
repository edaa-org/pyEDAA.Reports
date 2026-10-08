package my.pack;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class OtherClassTest {

	@Test
	void testReturnThree() {
		System.out.println("Output on STDOUT.");
		System.err.println("Output on STDERR.");
		assertEquals(3, new OtherClass().returnThree());
	}

}
