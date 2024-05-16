#include "Counter.hpp"

#include "gtest/gtest.h"

namespace {

TEST(Counter, Init) {
	Counter c0 { 0 };
	Counter c1 { 1 };
	EXPECT_EQ(0, c0.Value());
	EXPECT_EQ(1, c1.Value());
}

TEST(Counter, Increment) {
	Counter c { 0 };
	EXPECT_EQ(0, c.Increment());
	EXPECT_EQ(1, c.Value());
}

TEST(Counter, Decrement) {
	Counter c { 1 };
	EXPECT_EQ(1, c.Decrement());
	EXPECT_EQ(0, c.Value());
}

}  // namespace
