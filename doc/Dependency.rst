.. _DEP:

Dependencies
############

.. |img-Reports-lib-status| image:: https://img.shields.io/librariesio/release/pypi/pyEDAA.Reports
   :alt: Libraries.io status for latest release
   :height: 22
   :target: https://libraries.io/github/edaa-org/pyEDAA.Reports
.. |img-Reports-req-status| image:: https://img.shields.io/requires/github/pyEDAA/pyEDAA.Reports
   :alt: Requires.io
   :height: 22
   :target: https://requires.io/github/edaa-org/pyEDAA.Reports/requirements/?branch=main

+------------------------------------------+------------------------------------------+
| `Libraries.io <https://libraries.io/>`_  | `Requires.io <https://requires.io/>`_    |
+==========================================+==========================================+
| |img-Reports-lib-status|                 | |img-Reports-req-status|                 |
+------------------------------------------+------------------------------------------+


.. _dependency-package:

pyEDAA.Reports Package
**********************

+-----------------------------------------------------------------+-------------+-------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Package**                                                     | **Version** | **License**                                                                               | **Dependencies**                                                                                                                                       |
+=================================================================+=============+===========================================================================================+========================================================================================================================================================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__          | ≥8.2        | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.txt>`__    | *None*                                                                                                                                                 |
+-----------------------------------------------------------------+-------------+-------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| `ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml/>`__ | ≥0.18       | `MIT <https://sourceforge.net/p/ruamel-yaml/code/ci/default/tree/LICENSE>`__              | *Not yet evaluated.*                                                                                                                                   |
+-----------------------------------------------------------------+-------------+-------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                         | ≥5.3        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__                   | *Not yet evaluated.*                                                                                                                                   |
+-----------------------------------------------------------------+-------------+-------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+


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

+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| **Package**                                                         | **Version** | **License**                                                                            | **Dependencies**     |
+=====================================================================+=============+========================================================================================+======================+
| `pytest <https://GitHub.com/pytest-dev/pytest>`__                   | ≥8.3        | `MIT <https://GitHub.com/pytest-dev/pytest/blob/master/LICENSE>`__                     | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `pytest-cov <https://GitHub.com/pytest-dev/pytest-cov>`__           | ≥6.1        | `MIT <https://GitHub.com/pytest-dev/pytest-cov/blob/master/LICENSE>`__                 | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `Coverage <https://GitHub.com/nedbat/coveragepy>`__                 | ≥7.8        | `Apache License, 2.0 <https://GitHub.com/nedbat/coveragepy/blob/master/LICENSE.txt>`__ | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `mypy <https://GitHub.com/python/mypy>`__                           | ≥1.15       | `MIT <https://GitHub.com/python/mypy/blob/master/LICENSE>`__                           | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `typing-extensions <https://GitHub.com/python/typing_extensions>`__ | ≥4.13       | `PSF-2.0 <https://github.com/python/typing_extensions/blob/main/LICENSE>`__            | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+
| `lxml <https://GitHub.com/lxml/lxml>`__                             | ≥5.4        | `BSD 3-Clause <https://GitHub.com/lxml/lxml/blob/master/LICENSE.txt>`__                | *Not yet evaluated.* |
+---------------------------------------------------------------------+-------------+----------------------------------------------------------------------------------------+----------------------+


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

+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Package**                                                                                     | **Version**  | **License**                                                                                              | **Dependencies**                                                                                                                                     |
+=================================================================================================+==============+==========================================================================================================+======================================================================================================================================================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__                                          | ≥8.0         | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__                    | *None*                                                                                                                                               |
+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| `Sphinx <https://GitHub.com/sphinx-doc/sphinx>`__                                               | ≥8.1         | `BSD 3-Clause <https://GitHub.com/sphinx-doc/sphinx/blob/master/LICENSE>`__                              | *Not yet evaluated.*                                                                                                                                 |
+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| `sphinx_btd_theme <https://GitHub.com/buildthedocs/sphinx.theme>`__                             | ≥0.5.2       | `MIT <https://GitHub.com/buildthedocs/sphinx.theme/blob/master/LICENSE>`__                               | *Not yet evaluated.*                                                                                                                                 |
+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| !! `sphinx_fontawesome <https://GitHub.com/fraoustin/sphinx_fontawesome>`__                     | ≥0.0.6       | `GPL 2.0 <https://GitHub.com/fraoustin/sphinx_fontawesome/blob/master/LICENSE>`__                        | *Not yet evaluated.*                                                                                                                                 |
+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| `sphinx_autodoc_typehints <https://GitHub.com/agronholm/sphinx-autodoc-typehints>`__            | ≥2.5         | `MIT <https://GitHub.com/agronholm/sphinx-autodoc-typehints/blob/master/LICENSE>`__                      | *Not yet evaluated.*                                                                                                                                 |
+-------------------------------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+


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

+----------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Package**                                                                | **Version**  | **License**                                                                                              | **Dependencies**                                                                                                                                     |
+============================================================================+==============+==========================================================================================================+======================================================================================================================================================+
| `pyTooling <https://GitHub.com/pyTooling/pyTooling>`__                     | ≥8.4         | `Apache License, 2.0 <https://GitHub.com/pyTooling/pyTooling/blob/main/LICENSE.md>`__                    | *None*                                                                                                                                               |
+----------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
| `wheel <https://GitHub.com/pypa/wheel>`__                                  | ≥0.45        | `MIT <https://github.com/pypa/wheel/blob/main/LICENSE.txt>`__                                            | *Not yet evaluated.*                                                                                                                                 |
+----------------------------------------------------------------------------+--------------+----------------------------------------------------------------------------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+


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

+----------------------------------------------------------+--------------+-------------------------------------------------------------------------------------------+----------------------+
| **Package**                                              | **Version**  | **License**                                                                               | **Dependencies**     |
+==========================================================+==============+===========================================================================================+======================+
| `wheel <https://GitHub.com/pypa/wheel>`__                | ≥0.45        | `MIT <https://github.com/pypa/wheel/blob/main/LICENSE.txt>`__                             | *Not yet evaluated.* |
+----------------------------------------------------------+--------------+-------------------------------------------------------------------------------------------+----------------------+
| `Twine <https://GitHub.com/pypa/twine/>`__               | ≥6.1         | `Apache License, 2.0 <https://github.com/pypa/twine/blob/main/LICENSE>`__                 | *Not yet evaluated.* |
+----------------------------------------------------------+--------------+-------------------------------------------------------------------------------------------+----------------------+
