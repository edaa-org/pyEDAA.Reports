//! A counter, the code under test of the example.

/// The error returned, if a counter at zero is decremented.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Underflow;

/// A counter of non-negative values.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct Counter {
	value: u32,
}

impl Counter {
	/// Create a counter starting at `value`.
	pub fn new(value: u32) -> Self {
		Self { value }
	}

	/// Return the counter's value.
	pub fn value(&self) -> u32 {
		self.value
	}

	/// Increment the counter and return the value before incrementing.
	pub fn increment(&mut self) -> u32 {
		let previous = self.value;
		self.value += 1;
		previous
	}

	/// Decrement the counter and return the value before decrementing.
	///
	/// Panics, if the counter is zero.
	pub fn decrement(&mut self) -> u32 {
		match self.try_decrement() {
			Ok(previous) => previous,
			Err(Underflow) => panic!("counter underflow"),
		}
	}

	/// Decrement the counter and return the value before decrementing, or [`Underflow`], if the counter is zero.
	pub fn try_decrement(&mut self) -> Result<u32, Underflow> {
		let previous = self.value;
		if previous == 0 {
			return Err(Underflow);
		}
		self.value = previous - 1;
		Ok(previous)
	}

	/// Reset the counter to zero. Not tested: its lines stay uncovered.
	pub fn reset(&mut self) {
		self.value = 0;
	}
}

#[cfg(test)]
mod tests {
	use super::*;

	#[test]
	fn init() {
		assert_eq!(Counter::new(0).value(), 0);
		assert_eq!(Counter::new(1).value(), 1);
		assert_eq!(Counter::default().value(), 0);
	}

	#[test]
	fn increment() {
		let mut counter = Counter::new(1);
		assert_eq!(counter.increment(), 1);
		assert_eq!(counter.value(), 2);
	}

	#[test]
	fn decrement() {
		let mut counter = Counter::new(1);
		assert_eq!(counter.decrement(), 1);
		assert_eq!(counter.value(), 0);
	}

	#[test]
	#[should_panic(expected = "counter underflow")]
	fn decrement_underflow() {
		Counter::new(0).decrement();
	}

	#[test]
	fn try_decrement_underflow() -> Result<(), String> {
		match Counter::new(0).try_decrement() {
			Err(Underflow) => Ok(()),
			Ok(previous) => Err(format!("expected an underflow, got {previous}")),
		}
	}

	// Intended failure: increment returns the value before incrementing.
	#[test]
	fn failing() {
		let mut counter = Counter::new(1);
		assert_eq!(counter.increment(), 2);
	}

	// Intended failure: the test returns an error instead of panicking.
	#[test]
	fn failing_result() -> Result<(), Underflow> {
		Counter::new(0).try_decrement()?;
		Ok(())
	}

	// Intended failure: an unexpected panic escapes the test.
	#[test]
	fn panicking() {
		Counter::new(0).decrement();
	}

	// Intended failure: the test is expected to panic, but doesn't.
	#[test]
	#[should_panic]
	fn not_panicking() {
		Counter::new(1).decrement();
	}

	// Intended skip.
	#[test]
	#[ignore = "reset isn't tested yet"]
	fn reset() {
		let mut counter = Counter::new(5);
		counter.reset();
		assert_eq!(counter.value(), 0);
	}
}
