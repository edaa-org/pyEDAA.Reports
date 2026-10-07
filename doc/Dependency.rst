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


.. _DEP/package:

pyEDAA.Reports Package (Mandatory)
**********************************

Python packages pyEDAA.Reports requires at runtime.

.. rubric:: Manually Installing Package Requirements

Use the :file:`requirements.txt` file to install all dependencies via ``pip3`` or install the package directly from
PyPI (see :ref:`INSTALL`).

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r requirements.txt

.. rubric:: Dependency List

.. dependency-table:: package
   :caption: Mandatory dependencies of the pyEDAA.Reports package.
   :depth: 2


.. _DEP/testing:

Unit Testing / Coverage (Optional)
**********************************

Additional Python packages needed for testing and code coverage collection. These packages are only needed for
developers or on a CI server.

.. rubric:: Manually Installing Test Requirements

Use the :file:`tests/unit/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively
install the mandatory dependencies too. :file:`tests/requirements.txt` installs the requirements of unit tests,
application tests and static type checking at once.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r tests/unit/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r tests\unit\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: unittest
   :caption: Dependencies for unit testing and code coverage.
   :depth: 1


.. _DEP/apptesting:

Application Testing (Optional)
******************************

Additional Python packages needed to run the application tests, which exercise the installed :program:`pyedaa-reports`
command line rather than the package's classes. These packages are only needed for developers or on a CI server.

.. rubric:: Manually Installing Application Test Requirements

Use the :file:`tests/app/requirements.txt` file to install all dependencies via ``pip3``. The file will
recursively install the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r tests/app/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r tests\app\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: apptest
   :caption: Dependencies for application testing.
   :depth: 1


.. _DEP/typing:

Static Type Checking (Optional)
*******************************

Additional Python packages needed for static type checking. These packages are only needed for developers or on a CI
server.

.. rubric:: Manually Installing Type Checking Requirements

Use the :file:`tests/typing/requirements.txt` file to install all dependencies via ``pip3``. The file will
recursively install the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r tests/typing/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r tests\typing\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: typing
   :caption: Dependencies for static type checking.
   :depth: 1


.. _DEP/documentation:

Sphinx Documentation (Optional)
*******************************

Additional Python packages needed for documentation generation. These packages are only needed for developers or on a
CI server.

.. rubric:: Manually Installing Documentation Requirements

Use the :file:`doc/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively install
the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r doc/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r doc\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: documentation
   :caption: Dependencies for building this documentation.
   :depth: 1


.. _DEP/packaging:

Packaging (Optional)
********************

Python packages needed for installation package generation. These packages are only needed for developers or on a CI
server.

:file:`pyproject.toml` lists them as build requirements, so ``python3 -m build`` installs them itself.

.. list-table:: Dependencies for generating an installation package.
   :header-rows: 1
   :widths: 30 20 50

   * - Package
     - Version
     - License
   * - `setuptools <https://GitHub.com/pypa/setuptools>`__
     - ≥84.0
     - `MIT <https://GitHub.com/pypa/setuptools/blob/main/LICENSE>`__
   * - `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__
     - ≥9.0
     - `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__


.. _DEP/publishing:

Publishing (CI-Server only)
***************************

Additional Python packages needed for publishing the generated installation package to e.g, PyPI or any equivalent
services. These packages are only needed for maintainers or on a CI server.

.. rubric:: Manually Installing Publishing Requirements

Use the :file:`dist/requirements.txt` file to install all dependencies via ``pip3``. The file will recursively
install the mandatory dependencies too.

.. tab-set::

   .. tab-item:: Linux/macOS
      :sync: Linux

      .. code-block:: bash

         pip3 install -U -r dist/requirements.txt

   .. tab-item:: Windows
      :sync: Windows

      .. code-block:: powershell

         pip install -U -r dist\requirements.txt

.. rubric:: Dependency List

.. dependency-table:: publishing
   :caption: Dependencies for publishing the package.
   :depth: 1
