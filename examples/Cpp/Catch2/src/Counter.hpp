#ifndef COUNTER_H_
#define COUNTER_H_

class Counter {
	private:
		int _value;

	public:
		Counter(int value = 0);

		int Value();
		int Increment();
		int Decrement();
		void Reset();
};

#endif  // COUNTER_H_
