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
     - :class:`Requirement`            | e.g. ``EL-1`` - kind, obligation, state, layer, personas, labels, documents
       - :class:`Requirement`          | e.g. ``EL-1.1`` - a child requirement refining it
       - :class:`Link`                 | e.g. ``FW-1`` is the counterpart of ``EL-1``
       - :class:`HistoryEvent`         | e.g. opened, split, closed
     - :class:`SpecificationItem`      | e.g. ``DES-1`` - a specification item, which specifies requirements
       - :class:`SpecificationItem`    | e.g. ``DES-1.1`` - a child item detailing it

* The :class:`RequirementSpecification` registers every person by user ID, and every persona, label, document and layer,
  every requirement and every specification item - also the child items - by its ID. An ID is unique among the elements
  of a class; a duplicate raises the duplicate error of its class, e.g. :exc:`DuplicateRequirementError` - each a
  :exc:`~pyTooling.Exceptions.DuplicateElementError` and a :exc:`RequirementsError`. Each registry is a dictionary property,
  e.g. :attr:`~RequirementSpecification.Labels`, with an iterator taking an optional predicate, e.g.
  :meth:`~RequirementSpecification.IterateLabels`.
* The root's :attr:`~RequirementSpecification.Version` is the version of the specification itself; its name is
  optional.
* A :class:`Persona` is a role a user of the system acts in, e.g. an administrator, a reviewer or a quality inspector.
  A real person is a :class:`~pyEDAA.Reports.Person` with a user ID, a name and an optional e-mail address. A person
  has no parent: :meth:`~RequirementSpecification.AddPerson` registers it, and the same person may be registered in
  several specifications.
* Every element knows the element containing it - :attr:`~Base.Parent` - and its specification - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the specification on to the
  elements below it. An element, which already has a parent, raises an :exc:`AlreadyInSpecificationError` - an
  :exc:`~pyTooling.Exceptions.AlreadyInHierarchyError`.
* An item refers only to personas, labels, documents and layers of its own specification. An element or person of
  another specification raises a :exc:`NotInSameSpecificationError` - a :exc:`~pyTooling.Exceptions.NotInSameHierarchyError`:
  it is valid, but not part of the specification.


.. _REQ/Requirements:

Requirements
************

A :class:`Requirement` has an ID, a title, a description, a creation time - the current time, unless given - and a
:class:`RequirementKind`, which names what it constrains: e.g. a function, its performance, a quality, safety or
security, an interface, the environment, a design constraint or a regulation. Its :class:`Obligation` answers whether
it is mandatory or optional, by the levels of ISO/IEC/IEEE 29148 and RFC 2119:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Obligation
     - Keyword
     - Meaning
   * - ``mandatory``
     - *shall*, *must*
     - Binding; the default.
   * - ``recommended``
     - *should*
     - A goal; a deviation is justified.
   * - ``optional``
     - *may*
     - A permission.

Its :class:`ItemState` follows its life cycle from ``placeholder`` over ``draft``, ``in-review``, ``final`` and
``implemented`` to ``verified``; a new requirement is a ``draft``. A verified requirement is ``closed``, when it is
released and changes no more, e.g. in a baseline. At any time, a requirement can be ``rejected`` or become
``obsolete``.

A requirement belongs to at most one :class:`Layer`: the requirements of one engineering discipline, e.g. electrical,
mechanical, FPGA firmware or software. A layer partitions the requirements; a selection across layers - e.g. the
requirements of a product variant - is a :class:`Label`, or a predicate.

A requirement contains child requirements, which refine it. :meth:`~BaseItem.IterateChildren` iterates the children,
:meth:`~BaseItem.IterateDescendants` the children and grandchildren, depth-first.
:meth:`~RequirementSpecification.IterateRequirements` iterates every requirement of the specification. Each takes an
optional predicate to select the requirements:

.. code-block:: Python

   from pyTooling.Versioning import SemanticVersion
   from pyEDAA.Reports import Person
   from pyEDAA.Reports.Requirements import Layer, Requirement, RequirementKind, RequirementSpecification

   specification = RequirementSpecification(SemanticVersion(1, 0, 0), "Board")
   alice = Person("alice", "Alice", "alice@example.com")
   specification.AddPerson(alice)
   electrical = Layer("el", "Electrical", parent=specification)

   power = Requirement("EL-1", "Power supply", RequirementKind.Functional, layer=electrical, authors=[alice],
                       parent=specification)
   Requirement("EL-1.1", "Core rail", RequirementKind.Performance, "0.9 V, 5 A.", layer=electrical, parent=power)

   for requirement in specification.IterateRequirements(lambda r: r.Kind is RequirementKind.Performance):
     print(f"{requirement.ID}: {requirement.Title}")


.. _REQ/Specifications:

Specification Items
*******************

A :class:`SpecificationItem` mirrors a requirement - with an ID, a title, a state, a layer, persons, personas, labels,
documents, child items, links and a history - and states how the system meets requirements, e.g. a design decision or an
interface description. Specification items and requirements are in an N:M relation:
:attr:`SpecificationItem.Requirements` lists the requirements an item specifies, :attr:`Requirement.SpecificationItems`
the items specifying a requirement. :meth:`SpecificationItem.AddRequirement` maintains both sides.
:meth:`~RequirementSpecification.IterateSpecificationItems` iterates every specification item, with an optional
predicate.


.. _REQ/Links:

Links
*****

A :class:`Link` starts at an item - its source - and points to another item of the same specification, its
destination. A link is no element of the item hierarchy: it has no parent. The source lists it as an outbound link, the
destination as an inbound link. Its :class:`LinkKind` names the relationship: *source kind destination*.
:meth:`~BaseItem.LinkTo` and :meth:`~BaseItem.LinkFrom` create an outbound or inbound link of an item, with the
parameters of the link's constructor.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Link kind
     - The source ...
   * - ``refines``
     - states the destination in more detail, outside the item hierarchy.
   * - ``derives-from``
     - is derived from the destination, e.g. a firmware requirement from an electrical one.
   * - ``counterpart-of``
     - is the destination's counterpart in another layer.
   * - ``depends-on``
     - can only be met, if the destination is met.
   * - ``conflicts-with``
     - can't be met together with the destination.
   * - ``duplicates``
     - states the same as the destination.
   * - ``replaces``
     - replaces the destination, which is obsolete.
   * - ``relates-to``
     - has any other relationship to the destination.

A source has one link of a kind to a destination. :meth:`~BaseItem.IterateOutboundLinks` and
:meth:`~BaseItem.IterateInboundLinks` take an optional predicate, e.g. to follow the counterparts of a requirement
through the layers.


.. _REQ/Verification:

Verification and Traceability
*****************************

An item states its :attr:`~BaseItem.Rationale`: why a requirement exists, or why a design decision was taken. A
requirement names the :class:`VerificationMethod` flags verifying it - the inspection, analysis, demonstration and test
of ISO/IEC/IEEE 29148, plus simulation and formal verification - and its acceptance criteria.

:meth:`~BaseItem.IterateTrace` follows the links of an item transitively, :meth:`~BaseItem.IterateInboundTrace` the
inbound links; each item is reached once, also in a cycle. A predicate selects the links followed, e.g. the
counterparts of an electrical requirement through the FPGA firmware into the software:

.. code-block:: Python

   for item in electrical.IterateInboundTrace(lambda link: link.Kind is LinkKind.CounterpartOf):
     print(f"{item.ID} ({item.Layer.Name}): {item.Title}")


.. _REQ/History:

History
*******

An item's :attr:`~BaseItem.History` lists the events of its life cycle in chronological order: an event can't be
earlier than the item's creation or its last event; a time without a time zone is a local time. A
:class:`HistoryEvent` has an :class:`EventKind` - e.g. opened, modified, approved, split, merged, closed or
obsoleted -, a time, optionally the person causing it, and the other items involved: a split names the items a
requirement was split into, a merge the items it was merged with.
