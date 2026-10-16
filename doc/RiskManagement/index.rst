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
:class:`~pyEDAA.Reports.RiskManagement.RiskManagement`, holds every risk by its ID.

.. py:currentmodule:: pyEDAA.Reports.RiskManagement

.. tree::

   - :class:`RiskManagement`  | the risk register - version, key-value pairs
     - :class:`Risk`          | e.g. ``R1`` - title, description, probability, impact, state

* A risk's :class:`Probability` says how likely it occurs: from *low* (identified, but sleeping) to *occurred* (the
  risk is active and causes heavy effects). Its :class:`Impact` says how much delay it causes, if it occurs: from
  *low* (a few days) to *critical* (multiple weeks).
* A risk's :class:`RiskState` follows its life cycle: *open* or *on hold* while it is tracked; then either *solved* -
  its mitigations removed it - or *closed* - it isn't tracked anymore, without being solved, e.g. because it was
  accepted or its time has passed.
* A risk joins the register by naming it as its parent, in its constructor or by :attr:`~Base.Parent`. An ID is unique
  among the risks of a register; a second risk of the same ID is rejected.
* Every element - the register too - has key-value pairs for data the model doesn't name, e.g. an owner:
  ``risk["owner"] = "Paebbels"``.
* The register iterates its risks, optionally filtered by a predicate: :meth:`RiskManagement.IterateRisks`.

.. code-block:: Python

   from pyTooling.Versioning import SemanticVersion
   from pyEDAA.Reports.RiskManagement import Impact, Probability, Risk, RiskManagement, RiskState

   register = RiskManagement(SemanticVersion(1, 0, 0))
   foundry =  Risk("R1", "Late silicon", "The foundry is late.", Probability.Medium, Impact.High, parent=register)
   tools =    Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Medium, parent=register)
   foundry["owner"] = "Paebbels"
   tools.State = RiskState.Closed

   for risk in register.IterateRisks(lambda risk: risk.State is RiskState.Open):
     print(f"{risk.ID}: {risk.Title} ({risk.Probability}, {risk.Impact}), owner {risk['owner']}")
