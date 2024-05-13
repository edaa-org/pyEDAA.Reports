from unittest import TestCase


class C:
	_value: int

	def __init__(self, value: int = 0):
		self._value = value

	def Add(self, value: int) -> int:
		self._value += value
		return self._value

	def Sub(self, value: int) -> int:
		self._value -= value
		return self._value

	@property
	def Value(self) -> int:
		return self._value

	@Value.setter
	def Value(self, value: int):
		self._value = value


class Instantiation(TestCase):
	def test_NoParameter(self):
		a = C()

		self.assertEqual(0, a.Value)

	def test_Parameter(self):
		a = C(5)

		self.assertEqual(5, a.Value)


class Operations(TestCase):
	def test_Add(self):
		a = C(10)

		self.assertEqual(10, a.Value)
		self.assertEqual(15, a.Add(5))
		self.assertEqual(15, a.Value)

	def test_Sub(self):
		a = C(10)

		self.assertEqual(10, a.Value)
		self.assertEqual(8, a.Sub(2))
		self.assertEqual(8, a.Value)
