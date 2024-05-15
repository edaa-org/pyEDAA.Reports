#ifndef COUNTER_H_
#define COUNTER_H_

class Counter {
	private:
		int _value;

	public:
		Counter() : _value(0) {}

		int Value();
		int Increment();
		int Decrement();
};

#endif  // COUNTER_H_
