//! Tests whose outcome depends on the attempt, for nextest's retries.

#[cfg(test)]
mod tests {
	/// The attempt nextest runs a test in, starting at 1.
	fn attempt() -> u32 {
		std::env::var("NEXTEST_ATTEMPT").map_or(1, |value| value.parse().unwrap())
	}

	#[test]
	fn passing() {
		assert_eq!(1 + 1, 2);
	}

	// Intended flakiness: fails in the first attempt, passes in the retry.
	#[test]
	fn flaky() {
		assert!(attempt() > 1, "first attempt fails");
	}

	// Intended flakiness, configured to count as a failure.
	#[test]
	fn flaky_failing() {
		assert!(attempt() > 1, "first attempt fails");
	}

	// Intended failure: fails in every attempt.
	#[test]
	fn failing() {
		assert_eq!(attempt(), 0);
	}

	// Intended skip.
	#[test]
	#[ignore = "not run by default"]
	fn ignored() {}
}
