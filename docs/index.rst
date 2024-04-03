PyHam Paracon
=============

Overview
--------

Paracon is a packet radio terminal for Linux, Mac and Windows. It is focused
on simplicity and ease of use, and incorporates the core functionality that
most packet users need without trying to include all of the bells and whistles
that few would use.

Key features of Paracon include:

- Multiple simultaneous AX.25 connected mode sessions, allowing for connections
  to multiple BBS or other remote nodes.
- Unproto (UI, or datagram) AX.25 mode, allowing for keyboard-to-keyboard chat
  or other non-connected uses.
- Text-based console application looks and behaves the same on all supported
  platforms (Linux, Mac, Windows).
- Uses the AGWPE protocol to communicate with any server implementing that
  protocol. Tested and supported with Direwolf, ldsped and AGWPE.
- Self-contained executable requires only a Python installation to run, without
  the need to install any additional dependencies.

:Author: Martin F N Cooper, KD6YAM
:License: :doc:`MIT License <license>`

Installation
------------

.. important::
   This application requires Python 3.7 or later.

Download the latest release from GitHub.

#. Go to the
   `latest release <https://github.com/mfncooper/paracon/releases/latest>`__
   page.
#. In the *Assets* section, click on the Paracon ``.pyz`` file to download it.

You may download the ``.pyz`` file to any directory of your choosing. If you
are running on Linux or Mac, you may wish to place it in a directory that is
on your path.

The source code is available from the
`GitHub repository <https://github.com/mfncooper/paracon>`__:

.. code-block:: console

   $ git clone https://github.com/mfncooper/paracon

Running
-------

Before running Paracon, ensure that you have an AGWPE server (e.g. Direwolf,
ldsped or AGWPE) installed and running either on the same system or on a
remote system to which you have access. If you do not already have such a
server set up, see `References <#references>`__ below for more information.

Note that Paracon will create its configuration and log files in your *current
directory* when you start it, not the directory in which the ``.pyz`` file is
located.

To start Paracon, open a terminal window (Command Prompt or PowerShell on
Windows), change directory to a suitable location for your configuration and
log files, and type the following:

.. code-block:: console

   $ python3 <path-to-pyz-file>/paracon_<version>.pyz

Depending upon your particular system, you may need to substitute ``python``
for ``python3`` in the above command line, and of course backslash for slash
if you are running on Windows.

If you are running on Linux or Mac, the ``.pyz`` file is directly executable,
so that if you have placed it in a directory that is on your path, you can
simply type:

.. code-block:: console

   $ paracon_<version>.pyz

Documentation
-------------

:doc:`userguide`
   The User Guide takes you through all of the functionality of Paracon, from
   starting it the first time to using connected mode sessions and more.

References
----------

Direwolf
  Direwolf is probably the most widely used AGWPE server, and includes its own
  performant and robust AX.25 protocol stack. It is available for Linux, Mac
  and Windows. Open source.

  https://github.com/wb2osz/direwolf

ldsped
  ldsped is an alternative AGWPE server that runs on Linux, and relies on the
  Linux native AX.25 protocol stack. Open source.

  https://www.on7lds.net/42/node/2

AGWPE
  AGWPE is the original implementation of the protocol, and runs on Windows.
  Both free (AGWPE) and paid (Packet Engine Pro) versions are available.
  Proprietary; closed source.

  https://www.sv2agw.com/Home/downloads#packetenginePro

About PyHam
-----------

The PyHam name was borne of a need for unique names for Python packages that
were created for ham radio enthusiasts who are also software developers. Those
packages were themselves created out of a desire for a simpler way of building
sophisticated ham radio applications without the need to always start from
scratch. Paracon is one such application.

See the `PyHam home page <https://pyham.org>`__ for more information, and a
list of currently available libraries and applications.


.. toctree::
   :maxdepth: 2
   :hidden:

   Getting Started <self>
   userguide
   license
