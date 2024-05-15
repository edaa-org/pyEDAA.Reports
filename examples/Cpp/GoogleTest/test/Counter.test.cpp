#include "../src/Counter.hpp"

#include "gtest/gtest.h"

namespace {
TEST(Counter, Increment) {
	Counter c;

	EXPECT_EQ(0, c.Value());
	EXPECT_EQ(0, c.Increment());
	EXPECT_EQ(1, c.Value());

	EXPECT_EQ(1, c.Decrement());
	EXPECT_EQ(0, c.Value());
}

}  // namespace
