.. _RISK:

Risk Management
###############

Risk management identifies what may go wrong in a project, assesses how likely it is and how hard it would hit, and
tracks the measures against it. A risk register collects the risks of a project: each with its probability, its impact,
its state, the implications it has, if it occurs, and the mitigations reducing it.


.. _RISK/DataModel:

Data Model
**********

The risk management model of :mod:`pyEDAA.Reports.RiskManagement` is a risk register: the root,
:class:`~pyEDAA.Reports.RiskManagement.RiskManagement`, holds every risk, implication and mitigation by its ID. A risk
references its implications and mitigations, so several risks can share one.

.. py:currentmodule:: pyEDAA.Reports.RiskManagement

.. tree::

   - :class:`RiskManagement`  | the risk register - version, name, key-value pairs
     - :class:`Risk`          | e.g. ``R1`` - title, description, probability, impact, state, owner, next review
       - :class:`Link`        | e.g. ``R1`` causes ``R2`` - source, destination, kind
     - :class:`Implication`   | e.g. ``I1`` - a consequence, if a risk occurs
     - :class:`Mitigation`    | e.g. ``M1`` - a measure reducing a risk or an implication - kind, state

* A risk's :class:`Probability` says how likely it occurs: from *low* (identified, but sleeping) to *occurred* (the
  risk is active and causes heavy effects). Its :class:`Impact` says how much delay it causes, if it occurs: from
  *low* (a few days) to *critical* (multiple weeks).
* A risk's :attr:`~Risk.Score` is the rank of its probability times the rank of its impact, 1 to 16. The score
  classifies the risk by a :class:`RiskLevel` - see the matrix below -, e.g. to iterate the critical risks.
* A risk's :class:`RiskState` follows its life cycle: *open* or *on hold* while it is tracked; then either *solved* -
  its mitigations removed it - or *closed* - it isn't tracked anymore, without being solved, e.g. because it was
  accepted or its time has passed.
* An :class:`Implication` can have implications of its own, and it can be mitigated like a risk.
* A :class:`Mitigation` can have implications too: its side effects. So the same mitigation reduces a risk and a
  second-order implication, and its side effects are visible in the register.
* A risk's second-order implications (:attr:`Risk.SecondOrderImplications`) are the implications of its implications
  and the side effects of its mitigations.
* A mitigation's :class:`MitigationKind` says how it reduces a risk: it *avoids* its cause, *prevents* it - reduces its
  probability -, is a *contingency* plan applied, when the risk occurs, or *transfers* the impact to a third party. Its
  :class:`MitigationState` says whether it is applied: *on hold* - waiting to be planned -, *planned*, *active*, *done*
  or *abandoned*.
* A risk names its owner - the person responsible for it - and the date of its next review; a date without a time
  zone is a local time. The owner is a :class:`~pyEDAA.Reports.Person` - user ID, name, e-mail address -, which the
  register refers to (:meth:`RiskManagement.AddPerson`, :attr:`RiskManagement.Persons`). The same person may be
  registered in several registers, e.g. a register of risks and a specification of requirements.
* A :class:`Link` relates two risks of the same register: from its source to its destination, of a :class:`LinkKind` -
  e.g. *causes*, *amplifies*, *depends on*, *duplicates*. A link has no parent: both risks list it -
  :attr:`Risk.OutboundLinks` and :attr:`Risk.InboundLinks` -, and the register lists it in
  :attr:`RiskManagement.Links`. A source has at most one link of a kind to a destination. :meth:`Risk.LinkTo` and
  :meth:`Risk.LinkFrom` create an outbound or inbound link of a risk, with the parameters of the link's constructor.
* An element joins the register by naming it as its parent, in its constructor or by :attr:`~Base.Parent`. An ID is
  unique among the elements of its kind; a second element of the same ID raises a duplicate error of its kind, e.g.
  :exc:`DuplicateRiskError` - each a :exc:`~pyTooling.Exceptions.DuplicateElementError` and a
  :exc:`RiskManagementError`. An element already part of a register raises an :exc:`AlreadyInRiskRegisterError` - an
  :exc:`~pyTooling.Exceptions.AlreadyInHierarchyError`.
* An element of the register references only implications and mitigations of the same register, and a link connects
  risks of the same register: referenced elements and linked risks join the register first. Otherwise a
  :exc:`NotInSameRiskRegisterError` - a :exc:`~pyTooling.Exceptions.NotInSameHierarchyError` - is raised: the element is
  valid, but not part of the register. A risk's owner is a person of the register too.
* Every element - the register too - has key-value pairs for data the model doesn't name, e.g. a ticket:
  ``risk["ticket"] = "#42"``.
* The register iterates its risks, implications, mitigations and links, optionally filtered by a predicate, e.g.
  :meth:`RiskManagement.IterateRisks`.

.. list-table:: Risk level by probability and impact - the score in brackets
   :header-rows: 1
   :stub-columns: 1

   * - Probability
     - Impact low
     - medium
     - high
     - critical
   * - low
     - low (1)
     - low (2)
     - low (3)
     - medium (4)
   * - medium
     - low (2)
     - medium (4)
     - medium (6)
     - high (8)
   * - high
     - low (3)
     - medium (6)
     - high (9)
     - critical (12)
   * - occurred
     - medium (4)
     - high (8)
     - critical (12)
     - critical (16)

.. code-block:: Python

   from pyTooling.Versioning import SemanticVersion
   from pyEDAA.Reports import Person
   from pyEDAA.Reports.RiskManagement import Impact, Implication, LinkKind, Mitigation, MitigationKind
   from pyEDAA.Reports.RiskManagement import Probability, Risk, RiskLevel, RiskManagement

   register = RiskManagement(SemanticVersion(1, 0, 0), "Wafer tape-out")
   paebbels = Person("paebbels", "Patrick Lehmann", "paebbels@example.com")
   register.AddPerson(paebbels)
   budget =   Implication("I3", "The budget rises.", parent=register)
   shuttle =  Mitigation("M1", "Order a second shuttle run.", [budget], MitigationKind.Contingency, parent=register)
   launch =   Implication("I2", "The product launch is delayed.", parent=register)
   tapeOut =  Implication("I1", "The tape-out is delayed.", implications=[launch], parent=register)
   foundry =  Risk(
     "R1", "Late silicon", "The foundry delays the wafers.", Probability.High, Impact.High,
     implications=[tapeOut], mitigations=[shuttle], owner=paebbels, parent=register
   )
   foundry["ticket"] = "#42"
   board = Risk("R2", "Late board", "The board waits.", Probability.Medium, Impact.High, parent=register)
   foundry.LinkTo(board, LinkKind.Causes)

   for risk in register.IterateRisks(lambda risk: risk.Level in (RiskLevel.High, RiskLevel.Critical)):
     causes = [link.Destination.ID for link in risk.OutboundLinks if link.Kind is LinkKind.Causes]
     print(f"{risk.ID} {risk.Title} ({risk.Level}, owner {risk.Owner.Name}): causes {', '.join(causes)}")
     print(f"  second-order implications: {', '.join(risk.SecondOrderImplications)}")
