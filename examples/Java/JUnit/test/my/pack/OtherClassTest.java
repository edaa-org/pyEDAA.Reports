package my.pack;

import static org.junit.Assert.*;

import org.junit.Test;

public class OtherClassTest {

	@Test
	public void testReturnThree() {
		assertEquals(3, new OtherClass().returnThree());
	}

}
