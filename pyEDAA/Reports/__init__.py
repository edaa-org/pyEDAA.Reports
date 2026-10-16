# ==================================================================================================================== #
#              _____ ____    _        _      ____                       _                                              #
#  _ __  _   _| ____|  _ \  / \      / \    |  _ \ ___ _ __   ___  _ __| |_ ___                                        #
# | '_ \| | | |  _| | | | |/ _ \    / _ \   | |_) / _ \ '_ \ / _ \| '__| __/ __|                                       #
# | |_) | |_| | |___| |_| / ___ \  / ___ \ _|  _ <  __/ |_) | (_) | |  | |_\__ \                                       #
# | .__/ \__, |_____|____/_/   \_\/_/   \_(_)_| \_\___| .__/ \___/|_|   \__|___/                                       #
# |_|    |___/                                        |_|                                                              #
# ==================================================================================================================== #
# Authors:                                                                                                             #
#   Patrick Lehmann                                                                                                    #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
#                                                                                                                      #
# Licensed under the Apache License, Version 2.0 (the "License");                                                      #
# you may not use this file except in compliance with the License.                                                     #
# You may obtain a copy of the License at                                                                              #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
# Unless required by applicable law or agreed to in writing, software                                                  #
# distributed under the License is distributed on an "AS IS" BASIS,                                                    #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                                             #
# See the License for the specific language governing permissions and                                                  #
# limitations under the License.                                                                                       #
#                                                                                                                      #
# SPDX-License-Identifier: Apache-2.0                                                                                  #
# ==================================================================================================================== #
#
"""
Various report abstract data models and report format converters.
"""
from __future__            import annotations

__author__ =            "Patrick Lehmann"
__email__ =             "Paebbels@gmail.com"
__copyright__ =         "2021-2026, Electronic Design Automation Abstraction (EDA²)"
__license__ =           "Apache License, Version 2.0"
__version__ =           "0.20.0rc1"
__keywords__ =          ["Reports", "Abstract Model", "Data Model", "Unit Testing", "Testcase", "Testsuite", "OSVVM", "YAML", "XML"]
__project_url__ =       "https://github.com/edaa-org/pyEDAA.Reports"
__documentation_url__ = "https://edaa-org.github.io/pyEDAA.Reports"
__issue_tracker_url__ = "https://GitHub.com/edaa-org/pyEDAA.Reports/issues"

from enum                  import Enum
from typing                import Any, Iterator, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.Exceptions  import ExceptionBase
from pyTooling.MetaClasses import ExtendedType


@export
class ReportException(ExceptionBase):
	"""Base-exception of all exceptions raised by pyEDAA.Reports."""


@export
class Severity(Enum):
	Unknown = 0
	Debug = 5
	Verbose = 10
	Normal = 20
	Info = 25
	Warning = 50
	CriticalWarning = 55
	Error = 60
	Fatal = 70


@export
class KeyValuePairsMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding key-value pairs to an element of a data model, accessed with the dictionary syntax.

	``element[key]`` reads a value, ``element[key] = value`` creates or updates a pair, ``del element[key]`` removes it,
	``key in element`` asks for a key, ``len(element)`` counts the pairs, and iterating yields the keys.

	A data model iterates its elements by methods, not by iterating an element. As every element is iterable, a
	collection parameter of a data model rejects an element given in place of the collection explicitly.
	"""

	_keyValuePairs: dict[str, Any]  #: The key-value pairs, by key.

	def __init__(self, keyValuePairs: Nullable[Mapping[str, Any]] = None) -> None:
		"""
		Initialize the key-value pairs.

		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		"""
		self._keyValuePairs = {}

		if keyValuePairs is not None:
			if not isinstance(keyValuePairs, Mapping):
				ex = TypeError(f"Parameter 'keyValuePairs' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(keyValuePairs)}'.")
				raise ex

			for key, value in keyValuePairs.items():
				if not isinstance(key, str):
					ex = TypeError(f"Parameter 'keyValuePairs' contains a key not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
					raise ex
				elif key == "":
					raise ValueError(f"Parameter 'keyValuePairs' contains an empty key.")

				self._keyValuePairs[key] = value

	@readonly
	def KeyValuePairs(self) -> dict[str, Any]:
		"""
		Read-only property to access the key-value pairs (:attr:`_keyValuePairs`).

		:returns: The key-value pairs, by key.
		"""
		return self._keyValuePairs

	def __len__(self) -> int:
		"""
		Return the number of key-value pairs.

		:returns: The number of key-value pairs.
		"""
		return len(self._keyValuePairs)

	def __getitem__(self, key: str) -> Any:
		"""
		Return the value of a key.

		:param key:       The key.
		:returns:         The value.
		:raises KeyError: If the element has no pair of that key.
		"""
		return self._keyValuePairs[key]

	def __setitem__(self, key: str, value: Any) -> None:
		"""
		Create or update the key-value pair of a key.

		:param key:         The key.
		:param value:       The value.
		:raises ValueError: If parameter ``key`` is ``None``.
		:raises TypeError:  If parameter ``key`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``key`` is empty.
		"""
		if key is None:
			raise ValueError(f"Parameter 'key' is None.")
		elif not isinstance(key, str):
			ex = TypeError(f"Parameter 'key' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
			raise ex
		elif key == "":
			raise ValueError(f"Parameter 'key' is empty.")

		self._keyValuePairs[key] = value

	def __delitem__(self, key: str) -> None:
		"""
		Remove the key-value pair of a key.

		:param key:       The key.
		:raises KeyError: If the element has no pair of that key.
		"""
		del self._keyValuePairs[key]

	def __contains__(self, key: str) -> bool:
		"""
		Check whether the element has a key-value pair of a key.

		:param key: The key.
		:returns:   ``True``, if the element has a pair of that key.
		"""
		return key in self._keyValuePairs

	def __iter__(self) -> Iterator[str]:
		"""
		Iterate the keys of the key-value pairs.

		:returns: An iterator of the keys.
		"""
		return iter(self._keyValuePairs)


@export
class Person(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	A real person: a user ID, a name and an e-mail address.

	A person belongs to no single data model: a root registers the persons it refers to, and the same person may be
	registered in several roots, e.g. as the author of requirements and as the owner of risks. The role a person acts in,
	e.g. a reviewer, is a persona of the requirements model.
	"""

	_userID: str            #: The person's user ID, unique among persons.
	_name:   str            #: The person's name.
	_email:  Nullable[str]  #: The person's e-mail address, if known.

	def __init__(
		self,
		userID: str,
		name: str,
		email: Nullable[str] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> None:
		"""
		Initialize a person.

		:param userID:        The person's user ID, e.g. ``paebbels``.
		:param name:          The person's name.
		:param email:         Optional, the person's e-mail address. Default: ``None``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:   If parameter ``userID`` or ``name`` is ``None``.
		:raises TypeError:    If parameter ``userID``, ``name`` or ``email`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``userID`` or ``name`` is empty.
		:raises ValueError:   If parameter ``email`` isn't of the form ``local@domain``.
		"""
		super().__init__(keyValuePairs)

		for parameterName, text in (("userID", userID), ("name", name)):
			if text is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(text, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(text)}'.")
				raise ex
			elif text == "":
				raise ValueError(f"Parameter '{parameterName}' is empty.")

		if email is not None and not isinstance(email, str):
			ex = TypeError(f"Parameter 'email' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(email)}'.")
			raise ex
		elif email is not None and "" in email.partition("@"):
			ex = ValueError(f"Parameter 'email' isn't of the form 'local@domain'.")
			ex.add_note(f"Got value '{email}'.")
			raise ex

		self._userID = userID
		self._name =   name
		self._email =  email

	@readonly
	def UserID(self) -> str:
		"""
		Read-only property to access the person's user ID (:attr:`_userID`).

		:returns: The user ID, unique among persons.
		"""
		return self._userID

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the person's name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def Email(self) -> Nullable[str]:
		"""
		Read-only property to access the person's e-mail address (:attr:`_email`).

		:returns: The e-mail address, or ``None`` if unknown.
		"""
		return self._email

	def __repr__(self) -> str:
		"""
		Return a representation of the person.

		:returns: The user ID, the name and the e-mail address, if known.
		"""
		return f"<Person {self._userID}: {self._name}{'' if self._email is None else f' <{self._email}>'}>"

