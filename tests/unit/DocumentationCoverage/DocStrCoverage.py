from pathlib  import Path
from unittest import TestCase

from pyEDAA.Reports.DocumentationCoverage import CoverageState
from pyEDAA.Reports.DocumentationCoverage.Python import DocStrCoverage


class Analyze(TestCase):
	def test_Analyze(self) -> None:
		docStrCov = DocStrCoverage("pyEDAA.Reports", Path("pyEDAA"))
		docStrCov.Analyze()
		cov = docStrCov.Convert()
		cov.Aggregate()

		self.assertEqual(CoverageState.Unknown, cov.Status)
		self.assertGreaterEqual(cov.AggregatedCoverage, 0.20)
