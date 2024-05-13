from unittest import TestCase


class A:
	_value: int

	def __init__(self, value: int = 0):
		self._value = value

	@property
	def Value(self) -> int:
		return self._value

	@Value.setter
	def Value(self, value: int):
		self._value = value


class Instantiation(TestCase):
	def test_NoParameter(self):
		a = A()

		self.assertEqual(0, a.Value)

	def test_Parameter(self):
		a = A(5)

		self.assertEqual(5, a.Value)


class Properties(TestCase):
	def test_Getter(self):
		a = A(10)

		self.assertEqual(10, a.Value)

	def test_Setter(self):
		a = A(15)
		self.assertEqual(15, a.Value)

		a.Value = 20
		self.assertEqual(20, a.Value)
