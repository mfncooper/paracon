.. _user_guide:

User Guide
==========

Running Paracon
---------------

Paracon is a TUI application, which is to say it has a Text User Interface, and
runs in a terminal window. It is packaged as a zipapp, which is a self-contained
Python application. This makes running Paracon extremely easy. As long as you
have a suitable version of Python installed on your system, simply open a
terminal window (Command Prompt or PowerShell on Windows), change directory to
a suitable location for your configuration and log files, and enter:

.. code-block:: console

    $ python3 <path-to-pyz-file>/paracon_<version>.pyz

Depending upon your particular system, you may need to substitute ``python``
for ``python3`` in the above command line, and of course backslash for slash
if you are running on Windows.

On Linux and Mac, the pyz file is directly executable, so that if you have
placed it in a directory that is on your path, you can simply type:

.. code-block:: console

    $ paracon_<version>.pyz

Paracon will create its configuration and log files in your *current directory*
when you start it, not the directory in which the .pyz file is located, so you
should start it from wherever you would like these files to be created.

The first time you start Paracon, you will see the Setup window.

.. image:: /images/setup.png
   :alt: Setup window

Here you will enter the host and port of your AGWPE server (e.g. Direwolf),
along with the default callsign that Paracon should use to identify you.

Paracon will remember the information you enter here, so that when you start
the application on subsequent occasions, it will use this automatically. If
you need to change it later, you can bring up the Setup screen again.

Once you are successfully connected to the server, you will notice that the
host and port are displayed at the top right of the Paracon window.


Navigation
----------

.. admonition:: Navigation Cheat Sheet
   :class: tip

   **General**

   - Use either keystrokes or mouse clicks to navigate
   - Highlighted initial characters indicate available menu commands
   - Use Alt-<key> (Right-Option-<key> on Mac) to invoke a menu command
   - Yellow border indicates that panel has focus
   - Up, Dn, PgUp, PgDn keys scroll the focused panel

   **Dialogs**

   - Use arrow keys or mouse clicks to navigate within dialogs
   - Enter on the focused button invokes that command
   - Escape key cancels a dialog

   **Connections**

   - Alt-+ or Alt-t adds a connection tab
   - Alt-\- or Alt-r removes a connection tab
   - Alt-<digit> switches to the numbered tab


Connections
-----------

Once connected to your server, you'll see the Connections window.

.. image:: /images/connections.png
   :alt: Connections window

This is where you can open connected-mode sessions to remote systems. You can
open up to 9 simultaneous connections, each in its own tab. That '1:disc' in
the above screenshot indicates that tab #1 is currently disconnected.

To start a new connected-mode session, use the Connect command to bring up the
Connect dialog.

.. image:: /images/connect.png
   :alt: Connect dialog

Enter the callsign of the station to which you wish to connect, and any 'via'
you might need in order to reach it. (If you need to enter multiple 'via'
values, separate them with commas.) The 'My call' field will initially show
the callsign you entered at Setup time, but you can, of course, change it if
desired.

The 'Port' field is a drop-down list of the available AGWPE ports on your
server. Click on the down-arrow to open the list. In many cases, you will have
only one available port, and can leave this field as it is. If your server
provides multiple ports, you can select the appropriate one here.

Once you select 'Okay', Paracon will attempt to make a connection. Once it has
connected, your screen will change to something like the following.

.. image:: /images/connected.png
   :alt: Connected screen

As you can see, several things have been updated to reflect the new connection:

- The tab title now shows the callsign of the remote system to which you are
  connected.
- The connection status indicator on the bottom right of the Connections panel
  shows the details of your connection, including its duration.
- The 'Connect' command has been disabled, and 'Disconnect' has been enabled
  instead.

The tabbed panel for this connection shows Paracon's status as it makes the
attempt to connect, and then successfully connects. All of the traffic on this
connection, both incoming from the remote system and whatever you send to that
system, is also shown in this panel.

The Monitor panel shows all traffic seen on the AGWPE port. This includes the
traffic from your connected-mode session, and also any other traffic seen on
the same frequency.

Managing connections
~~~~~~~~~~~~~~~~~~~~

As mentioned above, you can open up to 9 simultaneous connections in Paracon.
To add a new connection, you simply create a new tab (using Alt-+ or Alt-t),
and connect to your new destination just as you did in the scenario described
above.

When you have multiple connections, you can switch between them with their
tab numbers (using Alt-<tab-number>).

When you are finished with a tab, you can either leave it open for future
reuse, or close it (using Alt-\- or Alt-r) to remove the clutter.

Unproto
-------

Switching from the Connections window to the Unproto window, you'll see a large
panel with the same content that you saw in the Monitor panel in the Connections
window, but here you have the opportunity to send Unproto (or unconnected)
messages too.

.. image:: /images/unproto.png
   :alt: Unproto window

Whatever you enter on the text entry line at the bottom will be sent out when
you hit the Return or Enter key.

The indicator on the bottom right shows the current configuration that will be
used for each message sent. To change this, use the Dest/Src command to bring
up the Unproto dialog.

.. image:: /images/unproto_cfg.png
   :alt: Unproto dialog

The 'Destination' field will initially show 'ID', but you should change this
depending upon your intended use of Unproto mode. (For example, if you are
participating in a net, it might be the callsign being used for that net.)

As with the Connect dialog, if you need to enter multiple ‘via’ values,
separate them with commas.

The 'Source' field will initially show the callsign you entered at Setup time,
but you can, of course, change it if desired.

The 'Port' field is a drop-down list of the available AGWPE ports on your
server. Click on the down-arrow to open the list. In many cases, you will have
only one available port, and can leave this field as it is. If your server
provides multiple ports, you can select the appropriate one here.

Settings
--------

Paracon will remember the information you enter in the Setup, Connect and
Unproto Dest/Src dialogs. When you bring up one of these dialogs, it will
initially show whatever values you had last entered.

These settings are saved in a text file named `paracon.cfg` in your current
directory when you started Paracon. Should you get into a confused state at
any time, you may simply delete this file. The next time you start Paracon,
it will start fresh with the Setup dialog.

If you need to maintain multiple Paracon configurations - perhaps different
setups for different servers, for example - you can do so simply by starting
Paracon from a different directory for each configuration.

Logging
-------

Paracon maintains a number of log files in the same directory as the Paracon
.pyz file.

paracon.log
   Contains information about any errors that have occurred during the
   execution of Paracon.

monitor.log
   Contains the same information as the Monitor and Unproto panels. This is
   preserved across Paracon sessions, making it easy to refer back to older
   data.
<call-from>_<call-to>.log
   Contains the exchange that occurs during a connection between the two
   stations of the filename. This is the same information that you see in the
   connection tab during a connected-mode session.
