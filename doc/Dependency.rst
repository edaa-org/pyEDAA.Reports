.. _DEP:

Dependencies
############

.. |img-Reports-lib-status| image:: https://img.shields.io/librariesio/release/pypi/pyEDAA.Reports
   :alt: Libraries.io status for latest release
   :height: 22
   :target: https://libraries.io/github/edaa-org/pyEDAA.Reports
.. |img-Reports-vul-status| image:: https://img.shields.io/snyk/vulnerabilities/github/edaa-org/pyEDAA.Reports
   :alt: Snyk Vulnerabilities for GitHub Repo
   :height: 22
   :target: https://img.shields.io/snyk/vulnerabilities/github/edaa-org/pyEDAA.Reports

+------------------------------------------+------------------------------------------+
| `Libraries.io <https://libraries.io/>`_  | Vulnerabilities Summary                  |
+==========================================+==========================================+
| |img-Reports-lib-status|                 | |img-Reports-vul-status|                 |
+------------------------------------------+------------------------------------------+


.. _dependency-package:

pyEDAA.Reports Package
**********************

+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| **Package**                                                     | **Version** | **License**                                                                           | **Dependencies**     |
+=================================================================+=============+=======================================================================================+======================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__          | ≥9.0        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__ | *None*               |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml/>`__ | ≥0.19       | `MIT <https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/LICENSE>`__          | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                         | ≥6.1        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__               | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+


.. _dependency-testing:

Unit Testing / Coverage / Type Checking (Optional)
**************************************************

Additional Python packages needed for testing, code coverage collection and static type checking. These packages are
only needed for developers or on a CI server, thus sub-dependencies are not evaluated further.


.. rubric:: Manually Installing Test Requirements

Use the :file:`tests/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively install
the mandatory dependencies too.

.. code-block:: shell

   pip3 install -U -r tests/requirements.txt


.. rubric:: Dependency List

+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| **Package**                                                              | **Version** | **License**                                                                            | **Dependencies**     |
+==========================================================================+=============+========================================================================================+======================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__                   | ≥9.0        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__  | *None*               |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml/>`__          | ≥0.19       | `MIT <https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/LICENSE>`__           | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                                  | ≥6.1        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__                | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `Coverage <https://GitHub.com/nedbat/coveragepy>`__                      | ≥7.15       | `Apache License, 2.0 <https://GitHub.com/nedbat/coveragepy/blob/master/LICENSE.txt>`__ | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `pytest <https://GitHub.com/pytest-dev/pytest>`__                        | ≥9.1        | `MIT <https://GitHub.com/pytest-dev/pytest/blob/master/LICENSE>`__                     | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `pytest-cov <https://GitHub.com/pytest-dev/pytest-cov>`__                | ≥7.1        | `MIT <https://GitHub.com/pytest-dev/pytest-cov/blob/master/LICENSE>`__                 | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `docstr_coverage <https://GitHub.com/HunterMcGushion/docstr_coverage>`__ | ≥2.3        | `MIT <https://GitHub.com/HunterMcGushion/docstr_coverage/blob/master/LICENSE>`__       | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `xmlschema <https://GitHub.com/sissaschool/xmlschema>`__                 | ≥4.3        | `MIT <https://GitHub.com/sissaschool/xmlschema/blob/master/LICENSE>`__                 | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `mypy <https://GitHub.com/python/mypy>`__                                | ≥2.3        | `MIT <https://GitHub.com/python/mypy/blob/master/LICENSE>`__                           | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `typing_extensions`                                                      | ≥4.16       | *Unknown.*                                                                             | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `lxml-stubs <https://GitHub.com/lxml/lxml-stubs>`__                      | ≥0.5        | `Apache License, 2.0 <https://GitHub.com/lxml/lxml-stubs/blob/master/LICENSE>`__       | *Not yet evaluated.* |
+--------------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+


.. _dependency-apptesting:

Application Testing (Optional)
******************************

Additional Python packages needed to run the application tests, which exercise the installed ``pyedaa-reports``
command line rather than the package's classes. These packages are only needed for developers or on a CI server,
thus sub-dependencies are not evaluated further.


.. rubric:: Manually Installing Application Test Requirements

Use the :file:`tests/app/requirements.txt` file to install all dependencies via ``pip3``. The file will
recursively install the mandatory dependencies too.

.. code-block:: shell

   pip3 install -U -r tests/app/requirements.txt


.. rubric:: Dependency List

+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| **Package**                                                     | **Version** | **License**                                                                           | **Dependencies**     |
+=================================================================+=============+=======================================================================================+======================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__          | ≥9.0        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__ | *None*               |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml/>`__ | ≥0.19       | `MIT <https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/LICENSE>`__          | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                         | ≥6.1        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__               | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `pytest <https://GitHub.com/pytest-dev/pytest>`__               | ≥9.1        | `MIT <https://GitHub.com/pytest-dev/pytest/blob/master/LICENSE>`__                    | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `xmlschema <https://GitHub.com/sissaschool/xmlschema>`__        | ≥4.3        | `MIT <https://GitHub.com/sissaschool/xmlschema/blob/master/LICENSE>`__                | *Not yet evaluated.* |
+-----------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+


.. _dependency-documentation:

Sphinx Documentation (Optional)
*******************************

Additional Python packages needed for documentation generation. These packages are only needed for developers or on a
CI server, thus sub-dependencies are not evaluated further.


.. rubric:: Manually Installing Documentation Requirements

Use the :file:`doc/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively install
the mandatory dependencies too.

.. code-block:: shell

   pip3 install -U -r doc/requirements.txt


.. rubric:: Dependency List

+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| **Package**                                                                          | **Version** | **License**                                                                                 | **Dependencies**     |
+======================================================================================+=============+=============================================================================================+======================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__                               | ≥9.0        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__       | *None*               |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml/>`__                      | ≥0.19       | `MIT <https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/LICENSE>`__                | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                                              | ≥6.1        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__                     | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `Sphinx <https://GitHub.com/sphinx-doc/sphinx>`__                                    | ≥9.1        | `BSD 3-Clause <https://GitHub.com/sphinx-doc/sphinx/blob/master/LICENSE>`__                 | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `docutils <https://docutils.sourceforge.io>`__                                       | ≥0.22       | `BSD 2-Clause <https://docutils.sourceforge.io/COPYING.html>`__                             | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `docutils_stubs <https://GitHub.com/tk0miya/docutils-stubs>`__                       | ≥0.0.22     | `Unlicense <https://GitHub.com/tk0miya/docutils-stubs/blob/master/LICENSE>`__               | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinx_rtd_theme <https://GitHub.com/readthedocs/sphinx_rtd_theme>`__               | ≥3.1        | `MIT <https://GitHub.com/readthedocs/sphinx_rtd_theme/blob/master/LICENSE>`__               | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinxcontrib-mermaid <https://GitHub.com/mgaitan/sphinxcontrib-mermaid>`__         | ≥2.1        | `BSD 2-Clause <https://GitHub.com/mgaitan/sphinxcontrib-mermaid/blob/master/LICENSE.rst>`__ | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinxcontrib-autoprogram <https://GitHub.com/sphinx-contrib/autoprogram>`__        | ≥0.1        | `BSD 2-Clause <https://GitHub.com/sphinx-contrib/autoprogram/blob/master/LICENSE>`__        | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `autoapi <https://autoapi.readthedocs.io>`__                                         | ≥2.0        | `Apache License, 2.0 <https://GitHub.com/carlos-jenkins/autoapi/blob/master/LICENSE>`__     | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinx_design <https://GitHub.com/executablebooks/sphinx-design>`__                 | ≥0.7        | `MIT <https://GitHub.com/executablebooks/sphinx-design/blob/main/LICENSE>`__                | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinx-copybutton <https://GitHub.com/executablebooks/sphinx-copybutton>`__         | ≥0.5        | `MIT <https://GitHub.com/executablebooks/sphinx-copybutton/blob/master/LICENSE>`__          | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinx_autodoc_typehints <https://GitHub.com/agronholm/sphinx-autodoc-typehints>`__ | ≥3.13       | `MIT <https://GitHub.com/agronholm/sphinx-autodoc-typehints/blob/master/LICENSE>`__         | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+
| `sphinx_reports <https://GitHub.com/pyTooling/sphinx_reports>`__                     | ≥0.11       | `Apache License, 2.0 <https://GitHub.com/pyTooling/sphinx_reports/blob/main/LICENSE.md>`__  | *Not yet evaluated.* |
+--------------------------------------------------------------------------------------+-------------+---------------------------------------------------------------------------------------------+----------------------+


.. _dependency-packaging:

Packaging (Optional)
********************

Additional Python packages needed for installation package generation. These packages are only needed for developers or
on a CI server, thus sub-dependencies are not evaluated further.


.. rubric:: Manually Installing Packaging Requirements

Use the :file:`build/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively
install the mandatory dependencies too.

.. code-block:: shell

   pip3 install -U -r build/requirements.txt


.. rubric:: Dependency List

+--------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| **Package**                                            | **Version** | **License**                                                                           | **Dependencies**     |
+========================================================+=============+=======================================================================================+======================+
| `setuptools <https://GitHub.com/pypa/setuptools>`__    | ≥84.0       | `MIT <https://GitHub.com/pypa/setuptools/blob/main/LICENSE>`__                        | *Not yet evaluated.* |
+--------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__ | ≥9.0        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__ | *None*               |
+--------------------------------------------------------+-------------+---------------------------------------------------------------------------------------+----------------------+


.. _dependency-publishing:

Publishing (CI-Server only)
***************************

Additional Python packages needed for publishing the generated installation package to e.g, PyPI or any equivalent
services. These packages are only needed for maintainers or on a CI server, thus sub-dependencies are not evaluated
further.


.. rubric:: Manually Installing Publishing Requirements

Use the :file:`dist/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively
install the mandatory dependencies too.

.. code-block:: shell

   pip3 install -U -r dist/requirements.txt


.. rubric:: Dependency List

+--------------------------------------------+-------------+---------------------------------------------------------------------------+----------------------+
| **Package**                                | **Version** | **License**                                                               | **Dependencies**     |
+============================================+=============+===========================================================================+======================+
| `wheel <https://GitHub.com/pypa/wheel>`__  | ≥0.47       | `MIT <https://github.com/pypa/wheel/blob/main/LICENSE.txt>`__             | *Not yet evaluated.* |
+--------------------------------------------+-------------+---------------------------------------------------------------------------+----------------------+
| `Twine <https://GitHub.com/pypa/twine/>`__ | ≥7.0        | `Apache License, 2.0 <https://github.com/pypa/twine/blob/main/LICENSE>`__ | *Not yet evaluated.* |
+--------------------------------------------+-------------+---------------------------------------------------------------------------+----------------------+
