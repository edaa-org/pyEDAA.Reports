.. _REQ:

Requirements
############

Requirements management records what a system must, should or may do, who wrote and owns each requirement, how it
evolved, and how the requirements of different engineering disciplines relate to each other: an electrical
requirement has its counterpart in the FPGA firmware, and this one in the software.


.. _REQ/DataModel:

Data Model
**********

The requirements model of :mod:`pyEDAA.Reports.Requirements` is built from typed values: no file format is read yet.
Every element carries key-value pairs for the information the model has no field for (``element["effort"] = 3``).

.. py:currentmodule:: pyEDAA.Reports.Requirements

.. tree::

   - :class:`RequirementSpecification` | the root - a version and an optional name
     - :class:`~pyEDAA.Reports.Person` | e.g. Patrick Lehmann - a real person: an author or owner of items
     - :class:`Persona`                | e.g. a reviewer - a role a user acts in, as in a user story
     - :class:`Label`                  | e.g. a product variant
     - :class:`Document`               | e.g. a datasheet - attached to items
     - :class:`Layer`                  | e.g. electrical, FPGA firmware or software

* The :class:`RequirementSpecification` registers every person by user ID, and every persona, label, document and layer
  by its ID. An ID is unique among the elements of a class; a duplicate is rejected.
* The root's :attr:`~RequirementSpecification.Version` is the version of the specification itself; its name is
  optional.
* A :class:`Persona` is a role a user of the system acts in, e.g. an administrator, a reviewer or a quality inspector.
  A real person is a :class:`~pyEDAA.Reports.Person` with a user ID, a name and an optional e-mail address. A person
  has no parent: :meth:`~RequirementSpecification.AddPerson` registers it, and the same person may be registered in
  several specifications.
* Every element knows the element containing it - :attr:`~Base.Parent` - and its specification - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the specification on to the
  elements below it.
