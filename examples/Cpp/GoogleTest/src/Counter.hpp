#ifndef COUNTER_H_
#define COUNTER_H_

class Counter {
	private:
		int _value;

	public:
		Counter(int value = 0) : _value { value } {}

		int Value();
		int Increment();
		int Decrement();
};

#endif  // COUNTER_H_
