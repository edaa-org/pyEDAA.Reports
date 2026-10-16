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

   - :class:`RequirementSpecification` | the root - a name and a version
     - :class:`Persona`                | e.g. an FPGA designer - an author or owner of items
     - :class:`Label`                  | e.g. a product variant
     - :class:`Document`               | e.g. a datasheet - attached to items
     - :class:`Layer`                  | e.g. electrical, FPGA firmware or software

* The :class:`RequirementSpecification` registers every persona, label, document and layer by its ID. An ID is unique
  among the elements of a class; a duplicate is rejected.
* The root's :attr:`~RequirementSpecification.Version` is the version of the specification itself.
* Every element knows the element containing it - :attr:`~Base.Parent` - and its specification - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the specification on to the
  elements below it.
