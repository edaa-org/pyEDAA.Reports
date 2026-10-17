//! Integration tests: the counter as seen by a user of the crate.

use counter::{Counter, Underflow};

#[test]
fn count_up_and_down() {
	let mut counter = Counter::new(0);
	for expected in 0..3 {
		assert_eq!(counter.increment(), expected);
	}
	for expected in (1..=3).rev() {
		assert_eq!(counter.decrement(), expected);
	}
	assert_eq!(counter.value(), 0);
}

#[test]
fn underflow() {
	let mut counter = Counter::new(1);
	assert_eq!(counter.try_decrement(), Ok(1));
	assert_eq!(counter.try_decrement(), Err(Underflow));
}

#[test]
fn printing_test() {
	println!("Output written to stdout by a passing test.");
	eprintln!("Output written to stderr by a passing test.");
}
