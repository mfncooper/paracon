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

On Linux and Mac, you can make the file directly executable, so that if you
have placed it in a directory that is on your path, you can simply type:

.. code-block:: console

    $ paracon_<version>.pyz

To enable this, you will need to set the necessary file permission using:

.. code-block:: console

    $ chmod u+x paracon_<version>.pyz

Paracon will create its configuration and log files in your *current directory*
when you start it, not the directory in which the .pyz file is located, so you
should start it from wherever you would like these files to be created.
(However, see :ref:`Settings` for information on alternative locations.)

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

.. _settings:

Settings
--------

Paracon will remember the information you enter in the Setup, Connect and
Unproto Dest/Src dialogs. When you bring up one of these dialogs, it will
initially show whatever values you had last entered.

These settings are saved, by default, in a text file named `paracon.cfg` in your
current directory when you started Paracon. Should you get into a confused state
at any time, you may simply delete this file. The next time you start Paracon,
it will start fresh with the Setup dialog.

If you need to maintain multiple Paracon configurations - perhaps different
setups for different servers, for example - you can do so simply by starting
Paracon from a different directory for each configuration. Alternatively, you
can specify the location of separate configuration files on the command line,
when you start Paracon. See :ref:`Command-line options <cli-options>` below.

Conversely, if you wish to share the same configuration file regardless of where
you start Paracon, you can move your `paracon.cfg` to your home directory after
Paracon initially creates it, and Paracon will find it there.

Text encodings
~~~~~~~~~~~~~~

When connected to a remote site (e.g. a BBS), Paracon interprets the text it
receives as UTF-8 encoded. In the overwhelming majority of circumstances, this
works as expected. However, on very rare occasions, content may be received
that was encoded using a different, non-compatible encoding. An example is
old line drawings created using the original IBM PC character set.

To allow for this, Paracon will try an alternate decoder if UTF-8 decoding
fails on a given line of text. If the alternate also fails, Paracon will revert
to UTF-8 but using the standard Unicode replacement character (�) in place of
any problem characters.

Why not allow for multiple alternate decoders? The problem is that it is not
possible for Paracon to determine which alternate is the correct one, because
the same character code may be a valid character in more than one alternate. As
an example, the degree symbol (°) in the old Windows encoding is a light shaded
box (░) in the original IBM PC encoding. The same character code (i.e. byte
value) is valid in both encodings, but the characters themselves are different.

By default, the alternate decoder is that for ``cp437``, which is the
aforementioned original IBM PC encoding. It is possible to change this if you
know for certain that you will be receiving content in a different encoding.
To specify a different alternate, you need to edit your `paracon.cfg` file and
add an entry like the following:

.. code-block:: console

    [Connect]
    decode_alt = cp1252

This example specifies that the old Windows encoding, ``cp1252``, should be
used as the alternate decoder instead of the default ``cp437``.

Color themes
~~~~~~~~~~~~

Paracon's colors can be customized by adding a ``[Theme]`` section to your
``paracon.cfg`` file. Each entry in this section overrides one of Paracon's
named color attributes by name. Attributes you do not specify retain their
default colors. Unrecognized attribute names are silently ignored.

.. code-block:: ini

    [Theme]
    monitor_call = light red, black
    monitor_own = light cyan, black
    menu_key = light yellow,bold, dark blue

Each entry takes the form::

    attribute_name = foreground, background

The foreground and background are separated by a comma followed by a space
(``", "``). The foreground may include text modifiers joined with a plain
comma and no space, for example ``light cyan,bold`` or
``white,bold,underline``. The full form with a modifier therefore looks
like::

    menu_key = light cyan,bold, dark blue

If you want to change only the foreground while keeping the default background,
you may omit the background value entirely (no trailing comma)::

    attribute_name = foreground

The following tables list all named attributes that can be overridden, along
with their default colors.

*Interface elements*

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Attribute
     - Default foreground
     - Default background
     - Controls
   * - ``menu_key``
     - ``light cyan,bold``
     - ``dark blue``
     - Highlighted shortcut letter in each menu command
   * - ``menu_text``
     - ``white``
     - ``dark blue``
     - Regular menu bar text
   * - ``tabbar_unsel``
     - ``black``
     - ``light gray``
     - Unselected connection tabs
   * - ``tabbar_sel``
     - ``white,bold``
     - ``black``
     - The currently selected connection tab
   * - ``dropdown_item``
     - ``white``
     - ``dark blue``
     - Items in a drop-down list
   * - ``dropdown_sel``
     - ``yellow,bold``
     - ``dark blue``
     - The currently highlighted drop-down item
   * - ``button_select``
     - ``white``
     - ``black``
     - Dialog buttons
   * - ``button_focus``
     - ``black``
     - ``light gray``
     - The currently focused dialog button
   * - ``dialog_back``
     - ``white``
     - ``dark blue``
     - Dialog background
   * - ``dialog_header``
     - ``black``
     - ``light gray``
     - Dialog title bar
   * - ``field_error``
     - ``light red``
     - ``dark blue``
     - Validation error messages in dialogs

*Windows*

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Attribute
     - Default foreground
     - Default background
     - Controls
   * - ``window_norm``
     - ``light gray``
     - ``black``
     - Unfocused window border
   * - ``window_sel``
     - ``yellow``
     - ``black``
     - Focused window border

*Monitor panel*

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Attribute
     - Default foreground
     - Default background
     - Controls
   * - ``monitor_text``
     - ``white``
     - ``black``
     - Body text of monitor entries
   * - ``monitor_call``
     - ``light green``
     - ``black``
     - Callsigns in received unproto frames
   * - ``monitor_own``
     - ``light magenta``
     - ``black``
     - Your own transmitted frames
   * - ``monitor_relayed``
     - ``yellow``
     - ``black``
     - Digipeaters that have relayed a packet and that we heard (those marked with ``*``)
   * - ``monitor_frame``
     - ``dark cyan``
     - ``black``
     - Frame type descriptor and timestamp (e.g. ``<UI pid=F0 Len=36 PF=0 >``, ``[21:52:43]``)

*Connection and Unproto panels*

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Attribute
     - Default foreground
     - Default background
     - Controls
   * - ``connection_inbound``
     - ``light cyan``
     - ``black``
     - Inbound connection status messages
   * - ``connection_outbound``
     - ``light magenta``
     - ``black``
     - Outbound connection status messages
   * - ``connection_error``
     - ``light red``
     - ``black``
     - Connection error messages
   * - ``unproto_error``
     - ``light red``
     - ``black``
     - Unproto error messages
   * - ``entry_line``
     - ``white``
     - ``black``
     - The text entry line at the bottom of the panel

Available colors
^^^^^^^^^^^^^^^^

The 16 standard **foreground** colors are:

    ``black``, ``dark red``, ``dark green``, ``brown``, ``dark blue``,
    ``dark magenta``, ``dark cyan``, ``light gray``, ``dark gray``,
    ``light red``, ``light green``, ``yellow``, ``light blue``,
    ``light magenta``, ``light cyan``, ``white``

The 8 standard **background** colors are:

    ``black``, ``dark red``, ``dark green``, ``brown``, ``dark blue``,
    ``dark magenta``, ``dark cyan``, ``light gray``

For both foreground and background, the special value ``default`` instructs
Paracon to use the terminal's own default color.

Text modifiers may be appended to a foreground color with a comma:
``bold``, ``underline``, ``standout``, ``italics``, ``blink``,
``strikethrough``. For example, ``light cyan,bold`` or
``white,bold,underline``.

If your terminal supports 256 colors, high-color values of the form
``h0``–``h255`` may be used, along with color-cube shortcuts such as
``#000``–``#fff`` and grayscale entries such as ``g0``–``g100``. Terminals
with 24-bit (true color) support also accept full hex codes in the form
``#rrggbb``. Support for these extended color formats varies across terminal
programs.

.. _cli-options:

Command-line options
--------------------

The default locations of the Paracon configuration and log files may be
overridden via command-line options, as follows.

-c, --config CONFIGFILE
   The full path to the configuration file used to save settings. If this file
   does not yet exist, Paracon will create it when new settings are saved.

-l, --logdir LOGDIR
   The full path to the directory in which Paracon should create its log files.
   If this directory does not exist, Paracon will create it on startup.

-V, --version
   Print out the Paracon version and exit.

Logging
-------

Paracon maintains a number of log files. By default, these are located in your
*current directory* when you start Paracon. Alternatively, you can specify a
log directory on the command line, when you start Paracon. See
:ref:`Command-line options <cli-options>` above.

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
