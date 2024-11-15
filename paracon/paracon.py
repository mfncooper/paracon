# =============================================================================
# Copyright (c) 2021-2024 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

__author__ = 'Martin F N Cooper'
__version__ = '1.1.0'

from enum import Enum
import logging
import re
from dotenv import load_dotenv
import os
import sys
import time
from typing import NamedTuple
import urwid

import ax25
import ax25.netrom
import config
import pserver
import urwidx

IS_WINDOWS = sys.platform == "win32"

XTPUSHCOLORS = '\x1b[#P'
XTPOPCOLORS = '\x1b[#Q'

_MAX_CALL_LENGTH = 9  # Base call (6) + '-' + ssid (2)

logger = logging.getLogger('paracon')

app = None

palette = [
    #
    # urwidx entries
    #

    # Menu
    ('menu_key', 'light cyan,bold', 'dark blue'),
    ('menu_text', 'white', 'dark blue'),

    # TabBar
    ('tabbar_unsel', 'black', 'light gray'),
    ('tabbar_sel', 'white,bold', 'black'),

    # Dropdown
    ('dropdown_item', 'white', 'dark blue'),
    ('dropdown_sel', 'yellow,bold', 'dark blue'),

    # ButtonSet
    ('button_select', 'white', 'black'),
    ('button_focus', 'black', 'light gray'),

    # Dialog
    ('dialog_back', 'white', 'dark blue'),
    ('dialog_header', 'black', 'light gray'),

    # FormDialog
    ('field_error', 'light red', 'dark blue'),

    #
    # paracon entries
    #

    # Windows
    ('window_norm', 'light gray', 'black'),
    ('window_sel', 'yellow', 'black'),

    # Monitor
    ('monitor_text', 'white', 'black'),
    ('monitor_call', 'light green', 'black'),

    # Connections
    ('connection_inbound', 'light cyan', 'black'),
    ('connection_outbound', 'light magenta', 'black'),
    ('connection_error', 'light red', 'black'),

    # Unproto
    ('unproto_error', 'light red', 'black'),

    # Line entry
    ('entry_line', 'white', 'black')
]


def is_command(key):
    if type(key) is str:
        parts = key.split()
        return len(parts) == 2 and parts[0] == 'meta'
    return False


def via_filter(widget, key):
    if widget.valid_char(key):
        if not (key.isalnum() or key in ('-', ' ', ',')):
            return None
        key = key.upper()
    return key


def callsign_filter(widget, key):
    if widget.valid_char(key):
        if (not (key.isalnum() or key == '-')
                or len(widget.edit_text) >= _MAX_CALL_LENGTH):
            return None
        key = key.upper()
    return key


class SizeListBox(urwid.ListBox):
    """
    Subclass of ListBox for the sole purpose of caching its size. The size
    must be passed in to many Urwid functions, including when determining
    the visibility of items, for example when scrolling.
    """
    def __init__(self, body):
        self._size = None
        super().__init__(body)

    @property
    def size(self):
        return self._size

    def render(self, size, focus=False):
        self._size = size
        return super().render(size, focus)


class Ports:
    """
    Per the AGWPE spec, port information comes from the server in the form
    "Portn xxxxxxx" for each port, where 'n' is the port number, and 'xxxxxxx'
    is the description. Some servers, notably Direwolf, may not use consecutive
    port numbers, so we need to parse the port numbers from these strings, and
    map between port numbers and indexes into the list of available ports.

    While known servers (Direwolf, ldsped, AGWPE) adhere to the string format
    in the spec, we need to allow for the possibility that some other server
    does not. In this case, the only thing we can do is revert to using the
    position in the list as the port number.

    Note that the port numbers reflected here are the API port numbers,
    which are 1 lower than the display port numbers, per the AGWPE spec.
    (That is, "Port1 ..." corresponds to API port 0, etc.)
    """
    def __init__(self, port_info):
        try:
            # Parse spec-defined "Portn xxxxxxx"
            port_nums = [int(s.split()[0][4:]) - 1 for s in port_info]
        except ValueError:
            # Fall back to using index as port number
            port_nums = [i for i, s in enumerate(port_info)]
        self._port_info = port_info
        self._port_nums = port_nums

    @property
    def port_info(self):
        return self._port_info

    def valid_port(self, port_num):
        return (port_num if port_num in self._port_nums
                else self._port_nums[0] if self._port_nums
                else None)

    def index_for_port(self, port_num):
        return (self._port_nums.index(port_num) if port_num in self._port_nums
                else 0)

    def port_for_index(self, ix):
        return (self._port_nums[ix] if ix < len(self._port_nums)
                else self._port_nums[0])

#---------------------------------------------------------------------------------------------------------------------------------
# =============================================================================
# Monitor
# =============================================================================

_INFO_LINE_PATTERN = re.compile(r"""
    ^\s*
    (?P<msg_port>\d)
    :Fm\s
    (?P<call_from>[A-Z0-9\-]+)
    \sTo\s
    (?P<call_to>[A-Z0-9\-]+)
    (?:\sVia\s(?P<call_via>[A-Z0-9\-\*\, ]+))?
    \s\<(?P<msg_info>.*)\>
    \[(?P<msg_time>[0-9\:]+)\]
    $
""", re.VERBOSE)


def _color_info_line(text):
    text = text.rstrip('\x00').rstrip()
    m = _INFO_LINE_PATTERN.match(text)
    if not m:
        return None
    line = [
        ('monitor_text', "{}:Fm ".format(m['msg_port'])),
        ('monitor_call', m['call_from']),
        ('monitor_text', " To "),
        ('monitor_call', m['call_to'])
    ]
    if m['call_via']:
        vias = m['call_via'].split(',')
        line.append(('monitor_text', " Via "))
        for via in vias:
            line.append(('monitor_call', via))
            line.append(('monitor_text', ','))
        line = line[:-1]
    line.append(
        ('monitor_text', " <{}>[{}]".format(m['msg_info'], m['msg_time'])))
    return line


class MonitorPanel(urwid.WidgetWrap):
    #first_message_saved = False  # Class attribute to track if the first message has been saved
    def __init__(self):
        self._log = urwidx.LoggingDequeListWalker([])
        self._list = SizeListBox(self._log)
        self._queue = None
        self._periodic_key = None
        super().__init__(self._list)
        self._log.set_logfile('monitor.log')
        urwid.connect_signal(app, 'server_started', self._start_monitor)
        urwid.connect_signal(app, 'server_stopping', self._stop_monitor)

    def _start_monitor(self, server):
        self._queue = server.monitor_queue
        self._periodic_key = app.start_periodic(1.0, self._update_from_queue)

    def _stop_monitor(self, server):
        if self._periodic_key:
            app.stop_periodic(self._periodic_key)
            self._periodic_key = None
            self._queue = None

    def _update_from_queue(self, obj):
        while not self._queue.empty():
            (kind, port, line) = self._queue.get()


            if (kind is pserver.MonitorType.UNPROTO_INFO or kind is pserver.MonitorType.CONN_INFO or kind is pserver.MonitorType.SUPER_INFO):
                clr_line = _color_info_line(line)
                if clr_line:
                    self.add_line(clr_line)
                else:
                    logger.debug("Coloring failed: {}".format(line))
                    self.add_line(line)
            elif (kind is pserver.MonitorType.UNPROTO_TEXT or kind is pserver.MonitorType.CONN_TEXT):
                self.add_multi_line(line)
            elif (kind is pserver.MonitorType.UNPROTO_NETROM
                    or kind is pserver.MonitorType.CONN_NETROM):
                if line[0] == 0xFF:  # only handle routing broadcasts
                    try:
                        rb = ax25.netrom.RoutingBroadcast.unpack(line)
                    except Exception:
                        logger.debug('Malformed NET/ROM data: {}'.format(line))
                        continue
                    self.add_line("NET/ROM Routing: {}".format(rb.sender))
                    if rb.destinations:
                        for d in rb.destinations:
                            self.add_line(
                                "   {!s:>9}   {:<6}   {!s:>9}   {:>3}".format(
                                    d.callsign,
                                    d.mnemonic,
                                    d.best_neighbor,
                                    d.best_quality))
        return True

    def add_line(self, line):
        # Skip if the ListBox has not yet been fully initialized
        if not self._list.size:
            return
        line = urwidx.safe_text(line)
        text = urwid.AttrMap(urwid.Text(line), 'monitor_text')
        # Save the state of visibility before appending new content
        ends_visible = self._list.ends_visible(self._list.size)
        self._log.append(text)
        # Auto-scroll only if the last entry is currently visible (i.e. the
        # user has not scrolled up to view earlier entries)
        if 'bottom' in ends_visible:
            self._list.set_focus(len(self._log) - 1, 'above')

    def add_multi_line(self, text):
        text = text.rstrip('\x00').rstrip().replace('\r\n', '\r')
        lines = text.split('\r')
        for line in lines:
            self.add_line(line)


class MonitorWindow(urwid.WidgetWrap):
    def __init__(self, mon):
        self._mon = mon
        self._box = urwid.AttrMap(urwid.LineBox(
            self._mon, title="Monitor", title_align='center'),
            'window_norm', 'window_sel')
        super().__init__(self._box)

    def get_pref_col(self, size):
        return 'left'

# =============================================================================
# Connections
# =============================================================================

class ConnectionPanel(urwid.WidgetWrap):

    first_message_saved = False  # Class attribute to track if the first message has been saved!!

    class MenuCommand(Enum):
        CONNECT = 'Connect'
        DISCONNECT = 'Disconnect'

    def __init__(self, panel_changed_callback):
        self._panel_changed_callback = panel_changed_callback
        self._connection = None
        self._connection_start = None
        self._timer_key = None
        self._periodic_key = None
        self._line_remains = ''
        self._log = urwidx.LoggingDequeListWalker([])
        self._list = SizeListBox(self._log)
        self._menubar = urwidx.MenuBar(self.MenuCommand)
        self._menubar.menu.enable(self.MenuCommand.DISCONNECT, False)
        self._set_info()
        urwid.connect_signal(
            self._menubar.menu, 'select', self._handle_menu_command)
        self._entry = urwidx.LineEntry(caption="> ", edit_text="")
        urwid.connect_signal(self._entry, 'line_entry', self._send)
        self._pile = urwid.Pile([
            ('weight', 1, self._list),
            (1, self._menubar),
            (1, urwid.AttrMap(urwid.Filler(self._entry), 'entry_line'))
        ])
        super().__init__(self._pile)

    @property
    def edit_widget(self):
        return self._entry

    @property
    def connected(self):
        return self._connection is not None

    def _connect(self):
        dlg = ConnectDialog()
        urwid.connect_signal(dlg, 'connect_info', self._save_and_connect)
        dlg.show(app._loop)

    def _save_and_connect(self, info):
        self._change_config(info)
        self._make_connection(info)

    def _change_config(self, info):
        config.set('Connect', 'connect_to', info.connect_to)
        config.set('Connect', 'connect_via', info.connect_via)
        config.set('Connect', 'connect_as', info.connect_as)
        config.set_int('Connect', 'port',
                       app.ports.port_for_index(info.port[0]))
        config.save_config()

    def _make_connection(self, info):
        registered = app.server.register_callsign(info.connect_as)
        if not registered:
            self.add_line((
                'connection_error',
                'Unable to register callsign. Cannot continue.'))
            self.add_line((
                'connection_error',
                'Your connection may be configured as readonly.'))
            return
        self._menubar.menu.enable(self.MenuCommand.CONNECT, False)
        port = app.ports.port_for_index(info.port[0])
        vias = info.connect_via.split() if info.connect_via else None
        conn = app.server.open_connection(
            port, info.connect_as, info.connect_to, vias)
        self._connection = conn
        self._periodic_key = app.start_periodic(1.0, self._update_from_queue)
        self.add_line('Connecting to {} ...'.format(info.connect_to))
        # Connection process will complete in _update_from_queue()

    def _disconnect(self):
        if self._connection:
            self._connection.close()
        self._menubar.menu.enable(self.MenuCommand.DISCONNECT, False)
        # Disconnection process will complete in _update_from_queue()

    def _reset(self):
        # Reset is similar to disconnect, except that the server disconnected
        # abruptly, so we need to reset without talking to the server. The
        # user has already been notified.
        self._panel_changed_callback(self, None)
        if self._connection:
            self._connection = None
            self._set_info()
        if self._periodic_key:
            app.stop_periodic(self._periodic_key)
            self._periodic_key = None
        self._log.set_logfile(None)
        self._menubar.menu.enable(
            self.MenuCommand.CONNECT, True)
        self._menubar.menu.enable(
            self.MenuCommand.DISCONNECT, False)

    def _send(self, widget, text):
        if self._connection:
            # Replace 'pgp' with 'hello' before sending
            if text == "pub":
                load_dotenv()
                text = os.getenv('PUB_KEY')
            try:
                self._connection.send_data(text + '\r')
            except BrokenPipeError:
                self.add_line(
                    ('connection_error', 'AGWPE server has disconnected'))
                app.server_disappeared()
            else:
                self.add_line(('connection_outbound', text))
        else:
            self.add_line(('connection_error', 'Not connected'))

    def _handle_menu_command(self, cmd):
        if cmd is self.MenuCommand.CONNECT:
            self._connect()
        elif cmd is self.MenuCommand.DISCONNECT:
            self._disconnect()

    def keypress(self, size, key):
        key = self._menubar.menu.keypress(size, key)
        return super().keypress(size, key)

    def _update_from_queue(self, obj):
        queue = self._connection.event_queue
        result = True

        while not queue.empty():
            (kind, data) = queue.get()
            if kind == 'status':
                if data == 'connected':
                    self._connection_start = time.time()
                    self._timer_key = app.start_periodic(1.0, self._set_info)
                    conn = self._connection
                    self._panel_changed_callback(self, conn)
                    self._log.set_logfile('{}_{}.log'.format(conn.call_from, conn.call_to))
                    self.add_line('Connected to {}'.format(conn.call_to))
                    self._menubar.menu.enable(self.MenuCommand.DISCONNECT, True)
                    #self._send(None, "Hello")
                elif data in ('connect-timeout', 'disconnected'):
                    self._panel_changed_callback(self, None)
                    if self._connection:
                        self._connection = None
                        self._set_info()
                    if self._timer_key:
                        app.stop_periodic(self._timer_key)
                        self._timer_key = None
                    if self._periodic_key:
                        app.stop_periodic(self._periodic_key)
                        self._periodic_key = None
                    if data == 'connect-timeout':
                        message = ('connection_error', 'Connection timed out')
                    else:
                        if self._connection_start:
                            message = 'Disconnected ({})'.format(self._format_duration())
                            self._connection_start = None
                        else:
                            message = 'Disconnected'
                    self.add_line(message)
                    self._log.set_logfile(None)
                    self._menubar.menu.enable(self.MenuCommand.CONNECT, True)
                    self._menubar.menu.enable(self.MenuCommand.DISCONNECT, False)
                    result = False
            elif kind == 'data':
                if not ConnectionPanel.first_message_saved:  # Check if the first message is not saved
                    print("Raw data:", data)  # Print raw data for debugging
                    try:
                        # Ignore the first two positions (characters) by slicing data[2:]
                        data = data[2:].decode('utf-8', errors='replace')  # Replace invalid bytes
                    except UnicodeDecodeError:
                        data = data[2:].decode('ISO-8859-1', errors='replace')  # Fallback if UTF-8 fails entirely
                    
                    with open('first_message.txt', 'w', encoding='utf-8', errors='replace') as f:  # Save the first message to a file
                        f.write(data)  # Write decoded data
                    ConnectionPanel.first_message_saved = True  # Mark the first message as saved
                else:  # Check if the first message is not saved
                    print("Not first Raw data:", data)  # Print raw data for debugging
                    try:
                        data = data.decode('utf-8', errors='replace')  # Replace invalid bytes
                    except UnicodeDecodeError:
                        data = data.decode('ISO-8859-1', errors='replace')  # Fallback if UTF-8 fails entirely
                    with open('recent_message.txt', 'w') as f:  # Save the first message to a file
                        f.write(data)  # Write decoded data
                    
                    

                self._gather_lines(data)
            else:
                logger.debug('Unknown queue entry: {}'.format(kind))
        return result

    def _gather_lines(self, data):
        if not isinstance(data, str):
            data = data.decode('utf-8')
        parts = data.split('\r')
        if len(self._line_remains):
            parts[0] = self._line_remains + parts[0]
            self._line_remains = ""
        if data[-1] != '\r':
            self._line_remains = parts[-1]
        del parts[-1]
        for part in parts:
            self.add_line(part)

    def add_line(self, line):
        text = urwid.Text(line)
        if type(line) is str:
            text = urwid.AttrMap(text, 'connection_inbound')
        # Save the state of visibility before appending new content
        ends_visible = self._list.ends_visible(self._list.size)
        self._log.append(text)
        # Auto-scroll only if the last entry is currently visible (i.e. the
        # user has not scrolled up to view earlier entries)
        if 'bottom' in ends_visible:
            self._list.set_focus(len(self._log) - 1, 'above')

    def _set_info(self, data=None):
        if self._connection:
            conn = self._connection
            duration = self._format_duration()
            text = "Connected to {} as {} ({}) ".format(
                conn.call_to, conn.call_from, duration)
        else:
            text = "Not connected "
        self._menubar.status = text
        return True

    def _format_duration(self):
        duration = time.time() - self._connection_start
        hr = int(duration // 3600)
        min = int(duration // 60)
        sec = int(duration % 60)
        return '{:02d}:{:02d}:{:02d}'.format(hr, min, sec)


class ConnectionWindow(urwid.WidgetWrap):
    DISCONNECTED = "disc"

    def __init__(self):
        self._tabs = urwidx.TabBar([self.DISCONNECTED])
        urwid.connect_signal(self._tabs, 'select', self._tab_selected)
        self._panels = [ConnectionPanel(self._panel_changed)]

        self._pile = urwid.Pile([
            (1, self._tabs),
            ('weight', 1, self._panels[0])
        ])
        self._box = urwid.AttrMap(
            urwid.LineBox(
                self._pile, title="Connections", title_align='center'),
            'window_norm', 'window_sel')
        super().__init__(self._box)
        urwid.connect_signal(app, 'server_stopping', self._server_stopping)

    @property
    def current_edit_widget(self):
        return self._pile.contents[1][0].edit_widget

    def _server_stopping(self, server):
        if not any([panel.connected for panel in self._panels]):
            return
        # If server is None, the server disconnected abruptly, so there's no
        # point in asking te user if they want to disconnect.
        if server is None:
            for panel in self._panels:
                if panel.connected:
                    panel._reset()
            return
        dlg = MessageBox(
            "Open Connections",
            [
                "One or more connections is still open.",
                "Do you want to disconnect?"
            ],
            ['Yes', 'No'])
        result = dlg.show_modal(app.loop)
        if result == 1:  # no, don't disconnect, cancel stopping
            return True
        for panel in self._panels:
            if panel.connected:
                panel._disconnect()

    def _tab_selected(self, old, new):
        self._pile.contents[1] = (
            self._panels[new[0] - 1],
            self._pile.contents[1][1])

    def _panel_changed(self, panel, connection):
        if connection:
            tab_name = connection.call_to
        else:
            tab_name = self.DISCONNECTED
        pos = self._panels.index(panel) + 1
        self._tabs.set_tab_name(pos, tab_name)

    def _add_panel(self):
        if len(self._panels) >= 9:
            # Tell the user we can't add any more
            return
        self._panels.append(ConnectionPanel(self._panel_changed))
        self._tabs.add_tab(self.DISCONNECTED)
        self._tabs.set_selected(len(self._panels))

    def _remove_panel(self):
        if len(self._panels) <= 1:
            # Tell the user we can't remove the last tab
            return
        # May need to ask user about disconnect if connected
        selected = self._tabs.get_selected()
        self._tabs.remove_tab(selected)
        panel = self._panels.pop(selected - 1)  # noqa F841
        # Do any cleanup we need to do - like disconnect?

    def keypress(self, size, key):
        if is_command(key):
            # Tab changes come here because tab bar is not selectable
            key = self._tabs.keypress(size, key)
            if not key:
                return None
            cmd = key[-1]
            if cmd == '+' or cmd.lower() == 't':
                self._add_panel()
                return None
            elif cmd == '-' or cmd.lower() == 'r':
                self._remove_panel()
                return None
        return super().keypress(size, key)

    def get_pref_col(self, size):
        return 'left'

    def mouse_event(self, size, event, button, col, row, focus):
        super().mouse_event(size, event, button, col, row, focus)



class ConnectionsScreen(urwid.WidgetWrap):
    def __init__(self, monitor_panel):
        self._connections_window = ConnectionWindow()
        self._monitor_window = MonitorWindow(monitor_panel)
        self._pile = urwid.Pile([
            ('weight', 2, self._connections_window),
            ('weight', 1, self._monitor_window)
        ])
        super().__init__(self._pile)

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key:
            edit = self._connections_window.current_edit_widget
            if edit:
                key = edit.keypress((size[0] - 2, ), key)
        return key

    def _update_from_queue(self):
        if self._connection:
            messages = self._connection.get_messages()
            for message in messages:
                self._connections_window.add_line(message)

    def _make_connection(self, info):
        registered = app.server.register_callsign(info.connect_as)
        if not registered:
            self._connections_window.add_line(
                ('connection_error', 'Unable to register callsign. Cannot continue.'))
            self._connections_window.add_line(
                ('connection_error', 'Your connection may be configured as readonly.'))
            return
        self._menubar.menu.enable(self.MenuCommand.CONNECT, False)
        port = app.ports.port_for_index(info.port[0])
        vias = info.connect_via.split() if info.connect_via else None
        conn = app.server.open_connection(
            port, info.connect_as, info.connect_to, vias)
        self._connection = conn
        self._periodic_key = app.start_periodic(1.0, self._update_from_queue)
        self._connections_window.add_line('Connecting to {} ...'.format(info.connect_to))

    def _disconnect(self):
        if self._connection:
            self._connection.close()
        self._menubar.menu.enable(self.MenuCommand.DISCONNECT, False)
        self._connections_window.add_line('Disconnected.')

    def _reset(self):
        self._panel_changed_callback(self, None)
        if self._connection:
            self._connection = None
            self._set_info()
        if self._periodic_key:
            app.stop_periodic(self._periodic_key)
            self._periodic_key = None
        self._log.set_logfile(None)
        self._connections_window.add_line('Connection reset.')
#--------------------------------------------------------------------------------------------------------------------------------------------------






# =============================================================================
# Application
# =============================================================================

class MonitorLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        if app:
            app.log_to_console(self.format(record))


class Application(metaclass=urwid.MetaSignals):
    signals = ['server_started', 'server_stopping']

    class MenuCommand(Enum):
        CONNECTIONS = 'Connections'
        UNPROTO = 'Unproto'
        SETUP = 'Setup'
        HELP = 'Help'
        ABOUT = 'About'
        QUIT = 'Quit'

    def __init__(self):
        self._palette = palette
        self._loop = None
        self._last_mouse_press = 0
        self._server = None
        self._ports = None
        self._debug_engine = False
        self._configure_logging()

    def _configure_logging(self):
        # Read configured settings
        level = self._get_logging_level('level') or logging.CRITICAL
        console = self._get_logging_level('console')
        engine = config.get_bool('Logging', 'engine')

        # We'll be configuring the PE logger as well as our own
        logger_pe = logging.getLogger('pe')

        # Create a file-based handler with format spec
        fmt = ("{asctime} [{name:11s}:{lineno:-4d}] "
               "[{levelname:7s}] {message}")
        fh = logging.FileHandler('paracon.log')
        fh.setFormatter(logging.Formatter(fmt, '%Y-%m-%d %H:%M:%S', '{'))

        # Add to both loggers
        logger.addHandler(fh)
        logger_pe.addHandler(fh)

        # Set level based on config value
        logger.setLevel(level)
        logger_pe.setLevel(level)

        # Add a handler for output to the monitor (screen)
        if console is not None:
            mh = MonitorLogHandler(console)
            # mh.setLevel(console)
            mh.setFormatter(logging.Formatter(fmt, style='{'))
            logger.addHandler(mh)

        # Save setting for when server is started
        self._debug_engine = engine

    def _get_logging_level(self, name):
        level = config.get('Logging', name)
        if level is not None:
            level = level.upper()
            level_val = logging.getLevelName(level)
            return level_val if isinstance(level_val, int) else None
        return None

    @property
    def loop(self):
        # Needed by dialogs
        return self._loop

    @property
    def server(self):
        return self._server

    @property
    def ports(self):
        return self._ports

    def _create_widgets(self):
        self._topbar = urwidx.MenuBar(self.MenuCommand)
        self._set_connected("not connected")
        self._topbar.menu.enable(self.MenuCommand.CONNECTIONS, False)
        urwid.connect_signal(
            self._topbar.menu, 'select', self._handle_menu_command)
        self._monitor_panel = MonitorPanel()
        self._connections_screen = ConnectionsScreen(self._monitor_panel)
        self._unproto_screen = UnprotoScreen(self._monitor_panel)
        self._frame = urwid.Frame(
            self._connections_screen, header=self._topbar)
        return self._frame

    def _handle_menu_command(self, cmd):
        if cmd is self.MenuCommand.UNPROTO:
            self._select_screen(self.MenuCommand.UNPROTO)
        elif cmd is self.MenuCommand.CONNECTIONS:
            self._select_screen(self.MenuCommand.CONNECTIONS)
        elif cmd is self.MenuCommand.SETUP:
            self._show_setup()
        elif cmd is self.MenuCommand.HELP:
            self._show_help()
        elif cmd is self.MenuCommand.ABOUT:
            self._show_about()
        elif cmd is self.MenuCommand.QUIT:
            self._quit()

    def _select_screen(self, screen):
        if screen is self.MenuCommand.CONNECTIONS:
            if self._frame.body != self._connections_screen:
                self._frame.body = self._connections_screen
                self._topbar.menu.enable(self.MenuCommand.CONNECTIONS, False)
                self._topbar.menu.enable(self.MenuCommand.UNPROTO, True)
        elif screen is self.MenuCommand.UNPROTO:
            if self._frame.body != self._unproto_screen:
                self._frame.body = self._unproto_screen
                self._topbar.menu.enable(self.MenuCommand.CONNECTIONS, True)
                self._topbar.menu.enable(self.MenuCommand.UNPROTO, False)

    def _show_setup(self):
        dlg = SetupDialog()
        urwid.connect_signal(dlg, 'setup_info', self._save_setup)
        dlg.show(self._loop)

    def _save_setup(self, setup_info):
        host = config.get('Setup', 'host')
        port = config.get_int('Setup', 'port')
        call = config.get('Setup', 'callsign')
        changed = False
        restart = False
        # If callsign changed, we don't immediately set the new value anywhere,
        # but we do need to save it.
        if setup_info.call != call:
            changed = True
        # If host or port changed, we need to restart the server
        if setup_info.host != host or setup_info.port != port:
            changed = True
            restart = True
        if changed:
            config.set('Setup', 'host', setup_info.host)
            config.set_int('Setup', 'port', setup_info.port)
            config.set('Setup', 'callsign', setup_info.call)
            config.save_config()
        if restart:
            self._server.stop()
            self._server = None
            self._ports = None
            self._loop.set_alarm_in(0, self._start_server)

    def _show_help(self):
        dlg = HelpBox()
        dlg.show(self._loop)

    def _show_about(self):
        dlg = AboutBox()
        dlg.show(self._loop)

    def _set_connected(self, server):
        self._topbar.status = "AGWPE Server: {}".format(server)

    def _quit(self):
        if self._server:
            # If there are open connections, and the user chooses not to close
            # them, then we won't quit. Otherwise all connections will have
            # been closed after the signal has been handled.
            if urwid.emit_signal(self, 'server_stopping', self._server):
                return
            self._server.stop()
        raise urwid.ExitMainLoop()

    def _unhandled_input(self, key):
        # Only handle key presses here
        if not isinstance(key, str):
            return False
        # Main menu commands come here because the top bar is not selectable
        if is_command(key):
            key = self._topbar.keypress(None, key)
            if not key:
                return True
        # Explicit handling for Help key
        if key == 'f1':
            self._handle_menu_command(self.MenuCommand.HELP)
            return True
        # Everything else
        return False

    def start_periodic(self, period, callback, data=None):
        def cb(loop, key):
            if callback(data):
                key[0] = self._loop.set_alarm_in(period, cb, key)
            else:
                key[0] = None
        k = [None]
        k[0] = self._loop.set_alarm_in(period, cb, k)
        return k

    def stop_periodic(self, key):
        if key and key[0]:
            self._loop.remove_alarm(key[0])
            key[0] = None

    def log_to_console(self, text):
        # Protect against logging before UI is ready
        if self._monitor_panel:
            self._monitor_panel.add_line(text)

    def _start_server(self, loop, data):
        startup = ServerStartup(loop)
        server = startup.start()
        if not server:
            raise urwid.ExitMainLoop()
        server.enable_debug(self._debug_engine)
        self._server = server
        self._ports = Ports(server.ports)
        self._set_connected('{}:{}'.format(
            config.get('Setup', 'host'), config.get_int('Setup', 'port')))
        self._server.register_callsign(config.get('Setup', 'callsign'))
        urwid.emit_signal(self, 'server_started', self._server)

    def server_disappeared(self):
        # This is called when the server has abruptly disconnected
        urwid.emit_signal(self, 'server_stopping', None)
        self._server.stop()
        self._server = None
        self._ports = None
        # Ask the user what they want to do now
        dlg = MessageBox(
            "Server Error",
            [
                "AGWPE server has disconnected",
                "Try to reconnect?"
            ],
            ['Reconnect', 'Exit'])
        result = dlg.show_modal(self._loop)
        if result == 0:  # Reconnect
            self._loop.set_alarm_in(0, self._start_server)
        else:
            raise urwid.ExitMainLoop()

    def run(self):
        self._loop = urwid.MainLoop(
            self._create_widgets(),
            palette=self._palette,
            pop_ups=True,
            input_filter=urwidx.mouse_double_press_filter,
            unhandled_input=self._unhandled_input)
        if not IS_WINDOWS:
            self._loop.screen.write(XTPUSHCOLORS)
            self._loop.screen.set_terminal_properties(16)
            self._loop.screen.reset_default_terminal_palette()
        self._loop.set_alarm_in(0, self._start_server)
        self._loop.run()
        if not IS_WINDOWS:
            self._loop.screen.write(XTPOPCOLORS)


class ServerStartup:
    """
    Encapsulates the complexity of ensuring that we have a valid config and
    can start the server. This includes telling the user about failures and
    then giving them options to resolve those failures, including editing
    the config, trying again, and exiting the application.
    """
    def __init__(self, loop):
        self._loop = loop
        self._info = None

    def start(self):
        """
        Start the process from the very beginning. The config that is read
        here may be missing values, if this is the first time the app has
        been started, or may now be invalid, if the server has changed.
        """
        self.read_config()
        return self.restart(False)

    def restart(self, force_ask=True):
        """
        First, ensure that we have a valid config. If we can't get that, bail
        out. Otherwise, attempt to connect to the server. If successful, save
        this working config.
        """
        info = self.collect_info(force_ask)
        if not info:
            return None
        server = self.start_server()
        if server:
            self.write_config()
        return server

    def collect_info(self, force_ask=True):
        """
        Collect setup info from the user. If force_ask is False and we already
        have all the values, just return. If force_ask is True, ask anyway,
        since this means that the config does not work (e.g. invalid server
        or port). Save the new config on success, and return True, or return
        False if the user chose to exit the application.
        """
        if (self._info.host and self._info.port
                and self._info.call and not force_ask):
            return True
        while True:
            info = self.ask_for_info()
            if info:
                break
            # User canceled; give them another chance
            result = self.ask_setup_exit()
            if result == 1:  # User chose Exit
                break
        if info:
            self._info = info
        return info is not None

    def start_server(self):
        """
        Attempt to connect to the server using the config we have. If this
        fails, tell the user and ask if they want to retry (e.g. if they
        forgot to start it), edit the config (e.g. something changed), or
        exit the application. On success, return the server we started.
        """
        server = pserver.Server()
        while True:
            message = None
            try:
                server.start(self._info.host, self._info.port)
            except pserver.ServerError as e:
                logger.debug('Server start error: {!r}'.format(e.root))
                message = e.message
            else:
                break
            result = self.ask_retry_setup_exit(message)
            if result == 2:  # User chose Exit
                return None
            if result == 1:  # User chose Setup
                return self.restart()
            # else user chose Retry, so loop
        return server

    def read_config(self):
        """
        Read the config from the user's config file (or default if this is
        the first time the application has been started.)
        """
        host = config.get('Setup', 'host')
        port = config.get_int('Setup', 'port')
        call = config.get('Setup', 'callsign')
        self._info = SetupDialog.SetupInfo(host, port, call)

    def write_config(self):
        """
        Write out a new working config. This should only be called when we
        have successfully started the server, so it is a 'known good' config.
        """
        config.set('Setup', 'host', self._info.host)
        config.set_int('Setup', 'port', self._info.port)
        config.set('Setup', 'callsign', self._info.call)
        config.save_config()

    def ask_for_info(self):
        """
        Bring up the Setup dialog to ask the user for config values. Return
        the new config on success, or None if the user chose to cancel. The
        config values will be superficially valid, but will be truly verified
        only when we attempt to start the server.
        """
        info = None

        def save_info(saved_info):
            nonlocal info
            info = saved_info

        dlg = SetupDialog(info)
        urwid.connect_signal(dlg, 'setup_info', save_info)
        dlg.show(self._loop, modal=True)
        return info

    def ask_setup_exit(self):
        """
        Ask the user if they wish to go back to setup or exit the app.
        """
        dlg = MessageBox(
            "Incomplete Configuration",
            "Cannot start without configuration",
            ['Setup', 'Exit'])
        return dlg.show_modal(self._loop)

    def ask_retry_setup_exit(self, message):
        """
        Ask the user if they wish to retry the connection attempt, edit the
        configuration, or give up and exit the app.
        """
        dlg = MessageBox(
            "Connection Failed",
            [
                "Could not connect to AGWPE server",
                "Reason: {}".format(message)
            ],
            ['Retry', 'Setup', 'Exit'])
        return dlg.show_modal(self._loop)


# =============================================================================
# Dialogs
# =============================================================================

class MessageBox(urwidx.Dialog):
    def __init__(self, title, message, buttons=['OK']):
        self._message = message
        self._index = -1
        super().__init__(title, buttons, 0)
        urwid.connect_signal(self, 'dialog_button', self._button_pressed)

    def get_body(self):
        if isinstance(self._message, list):
            msg_lines = [urwid.Text(msg, 'center') for msg in self._message]
        else:
            msg_lines = [urwid.Text(self._message, 'center')]
        return urwid.Pile([
            urwid.Divider(),
            *msg_lines,
            urwid.Divider()
        ])

    def show_modal(self, loop):
        self.show(loop, modal=True)
        return self._index

    def _button_pressed(self, index):
        self._index = index
        return True


class AboutBox(urwidx.Dialog):
    def __init__(self):
        super().__init__("About", ['Okay'], 0)
        urwid.connect_signal(self, 'dialog_button', self._button_pressed)

    def get_body(self):
        year = time.localtime().tm_year
        return urwid.Pile([
            urwid.Divider(),
            urwid.Text("Paracon", 'center'),
            urwid.Text("Packet Radio Console", 'center'),
            urwid.Text("Version " + __version__, 'center'),
            urwid.Divider(),
            urwid.Text(
                f"(c) 2021-{year}, Martin F N Cooper, KD6YAM", 'center'),
            urwid.Divider()
        ])

    def _button_pressed(self, index):
        return True


class HelpBox(urwidx.Dialog):
    def __init__(self):
        super().__init__("Help", ['Okay'], 0)
        urwid.connect_signal(self, 'dialog_button', self._button_pressed)

    def get_body(self):
        help_text = [
            " * Use Alt-<key> or mouse for commands",
            "    * Use Right-Option-<key> on Mac",
            " * Alt-+ or Alt-t adds connection tab",
            " * Alt-- or Alt-r removes connection tab",
            " * Cyan keys show available commands",
            " * Yellow border indicates panel has focus",
            " * Up, Dn, PgUp, PgDn scroll focused panel",
            " * Escape key cancels dialog"
        ]
        help_items = [urwid.Text(text, 'left') for text in help_text]
        return urwid.Pile([
            urwid.Divider(),
            *help_items,
            urwid.Divider()
        ])

    def _button_pressed(self, index):
        return True


class SetupDialog(urwidx.FormDialog):
    signals = ['setup_info']

    class SetupInfo(NamedTuple):
        host: str
        port: int
        call: str

    def __init__(self, info=None):
        self._info = info
        super().__init__("Setup")

    def add_fields(self):
        if self._info:
            host = self._info.host
            port = self._info.port
            call = self._info.call
        else:
            host = config.get('Setup', 'host') or ''
            port = config.get_int('Setup', 'port') or 0
            call = config.get('Setup', 'callsign') or ''
        self.add_group('server', "AGWPE Server")
        self.add_edit_str_field(
            'host', 'Host', group='server', value=host)
        self.add_edit_int_field(
            'port', 'Port', group='server', value=port)
        self.add_group('callsign', "Your callsign")
        self.add_edit_str_field(
            'call', 'Callsign', group='callsign', value=call,
            filter=callsign_filter)

    def validate(self):
        host = self.get_edit_str_value('host')
        port = self.get_edit_int_value('port')
        call = self.get_edit_str_value('call')
        if not (host and port and call):
            return "All fields are required"
        if not ax25.Address.valid_call(call):
            return "Invalid callsign"
        return None

    def save(self):
        host = self.get_edit_str_value('host')
        port = self.get_edit_int_value('port')
        call = self.get_edit_str_value('call').upper()
        info = self.SetupInfo(host, port, call)
        urwid.emit_signal(self, 'setup_info', info)


class ConnectDialog(urwidx.FormDialog):
    signals = ['connect_info']

    class ConnectInfo(NamedTuple):
        connect_to: str
        connect_via: str
        connect_as: str
        port: tuple

    def __init__(self, info=None):
        self._info = info
        super().__init__("Connect")

    def add_fields(self):
        if self._info:
            connect_to = self._info.connect_to
            connect_via = self._info.connect_via
            connect_as = self._info.connect_as
            port_ix = self._info.port[0]
        else:
            connect_to = config.get('Connect', 'connect_to') or ''
            connect_via = config.get('Connect', 'connect_via') or ''
            connect_as = (config.get('Connect', 'connect_as')
                          or config.get('Setup', 'callsign')
                          or '')
            port = config.get_int('Connect', 'port')
            # Ensure a valid index into list of ports
            if port is not None:
                port = app.ports.valid_port(port)
            if port is not None:
                port_ix = app.ports.index_for_port(port)
            else:
                port_ix = 0
        # Vias are saved with spaces, but displayed with commas
        connect_via = ','.join(connect_via.split())
        avail_ports = app.ports.port_info
        self.add_group('dest', "Connect To")
        self.add_edit_str_field(
            'connect_to', 'Call', group='dest', value=connect_to,
            filter=callsign_filter)
        self.add_edit_str_field(
            'connect_via', ' Via', group='dest', value=connect_via,
            filter=via_filter)
        self.add_group('source', "Connect Using")
        self.add_edit_str_field(
            'connect_as', 'My call', group='source', value=connect_as,
            filter=callsign_filter)
        self.add_dropdown_field(
            'port', '   Port', avail_ports, port_ix, group='source')

    def validate(self):
        connect_to = self.get_edit_str_value('connect_to')
        connect_via = self.get_edit_str_value('connect_via')
        connect_as = self.get_edit_str_value('connect_as')
        if not connect_to or not connect_as:
            return "Call and My call are required"
        if not ax25.Address.valid_call(connect_to):
            return "Call is invalid"
        if not ax25.Address.valid_call(connect_as):
            return "My call is invalid"
        if connect_via:
            vias = re.findall("[A-Za-z0-9-]+", connect_via)
            if not vias:
                return "Invalid via"
            for via in vias:
                if not ax25.Address.valid_call(via):
                    return "Invalid via"
        return None

    def save(self):
        connect_to = self.get_edit_str_value('connect_to').upper()
        connect_via = self.get_edit_str_value('connect_via').upper()
        connect_as = self.get_edit_str_value('connect_as').upper()
        port = self.get_dropdown_value('port')
        # The user may have used comma separators or something else, but we
        # standardize here on spaces.
        vias = re.findall("[A-Z0-9-]+", connect_via)
        info = self.ConnectInfo(connect_to, ' '.join(vias), connect_as, port)
        urwid.emit_signal(self, 'connect_info', info)


class UnprotoDialog(urwidx.FormDialog):
    signals = ['unproto_info']

    class UnprotoInfo(NamedTuple):
        src: str
        dst: str
        via: str
        port: tuple

    def __init__(self, info=None):
        self._info = info
        super().__init__("Unproto")

    def add_fields(self):
        if self._info:
            src = self._info.src
            dst = self._info.dst
            via = self._info.via
            port_ix = self._info.port[0]
        else:
            src = (config.get('Unproto', 'source')
                   or config.get('Setup', 'callsign')
                   or '')
            dst = config.get('Unproto', 'destination') or ''
            via = config.get('Unproto', 'via') or ''

            port = config.get_int('Unproto', 'port')
            # Ensure a valid index into list of ports
            if port is not None:
                port = app.ports.valid_port(port)
            if port is not None:
                port_ix = app.ports.index_for_port(port)
            else:
                port_ix = 0
        # Vias are saved with spaces, but displayed with commas
        via = ','.join(via.split())
        avail_ports = app.ports.port_info
        self.add_group('dest', "Send To")
        self.add_edit_str_field(
            'dst', 'Destination', group='dest', value=dst,
            filter=callsign_filter)
        self.add_edit_str_field(
            'via', '        Via', group='dest', value=via,
            filter=via_filter)
        self.add_group('source', "Send Using")
        self.add_edit_str_field(
            'src', 'Source', group='source', value=src,
            filter=callsign_filter)
        self.add_dropdown_field(
            'port', '  Port', avail_ports, port_ix, group='source')

    def validate(self):
        src = self.get_edit_str_value('src')
        dst = self.get_edit_str_value('dst')
        via = self.get_edit_str_value('via')
        if not (src and dst):
            return "Both source and destination are required"
        if not ax25.Address.valid_call(src):
            return "Source is invalid"
        if not ax25.Address.valid_call(dst):
            return "Destination is invalid"
        if via:
            vias = re.findall("[A-Za-z0-9-]+", via)
            if not vias:
                return "Invalid via"
            for v in vias:
                if not ax25.Address.valid_call(v):
                    return "Invalid via"
        return None

    def save(self):
        src = self.get_edit_str_value('src').upper()
        dst = self.get_edit_str_value('dst').upper()
        via = self.get_edit_str_value('via').upper()
        port = self.get_dropdown_value('port')
        # The user may have used comma separators or something else, but we
        # standardize here on spaces.
        vias = re.findall("[A-Z0-9-]+", via)
        info = self.UnprotoInfo(src, dst, ' '.join(vias), port)
        urwid.emit_signal(self, 'unproto_info', info)



# =============================================================================
# Unproto
# =============================================================================

class UnprotoScreen(urwid.WidgetWrap):

    class MenuCommand(Enum):
        CONFIGURE = 'Dest/Src'

    def __init__(self, mwin):
        self._mon = mwin
        self._menubar = urwidx.MenuBar(self.MenuCommand)
        self._set_info()
        urwid.connect_signal(
            self._menubar.menu, 'select', self._handle_menu_command)
        self._entry = urwidx.LineEntry(caption="> ", edit_text="")
        urwid.connect_signal(self._entry, 'line_entry', self._send)
        self._pile = urwid.Pile([
            ('weight', 1, self._mon),
            (1, self._menubar),
            (1, urwid.AttrMap(urwid.Filler(self._entry), 'entry_line'))
        ])
        super().__init__(urwid.AttrMap(urwid.LineBox(
            self._pile, title="Unproto", title_align='center'), 'window_norm'))
        urwid.connect_signal(app, 'server_started', self._update_info)

    def _send(self, widget, text):
        if not app.server:
            self._mon.add_line(
                ('unproto_error', 'Not connected to AGWPE server'))
            return
        src = config.get('Unproto', 'source')
        if not src:
            src = config.get('Setup', 'callsign')
        dst = config.get('Unproto', 'destination')
        via = config.get('Unproto', 'via')
        port = config.get_int('Unproto', 'port')
        if port is not None:
            port = app.ports.valid_port(port)
        if port is None:
            port = app.ports.port_for_index(0)
        if not self._valid_config(src, dst, via):
            self._mon.add_line(('unproto_error', 'Unproto config is invalid'))
            return
        vias = via.split() if via else None
        try:
            app.server.send_unproto(port, src, dst, text, vias)
        except BrokenPipeError:
            self._mon.add_line(
                ('unproto_error', 'AGWPE server has disconnected'))
            app.server_disappeared()

    def _valid_config(self, src, dst, via):
        if not (src and ax25.Address.valid_call(src)
                and dst and ax25.Address.valid_call(dst)):
            return False
        if via:
            vias = via.split()
            for v in vias:
                if not ax25.Address.valid_call(v):
                    return False
        return True

    def _handle_menu_command(self, cmd):
        if cmd is self.MenuCommand.CONFIGURE:
            self._configure()

    def keypress(self, size, key):
        key = self._menubar.keypress(size, key)
        if key:
            key = super().keypress(size, key)
        if key:
            # If the key hasn't been handled already, let the line entry
            # widget see if it wants it. This allows someone to type into
            # that widget without the focus having to be put there first.
            #
            # We "know" that the edit widget spans the screen, minus
            # the widget of the border around the Unproto window.
            key = self._entry.keypress((size[0] - 2, ), key)
        return key

    def _configure(self):
        dlg = UnprotoDialog()
        urwid.connect_signal(dlg, 'unproto_info', self._change_config)
        dlg.show(app._loop)

    def _change_config(self, info):
        config.set('Unproto', 'source', info.src)
        config.set('Unproto', 'destination', info.dst)
        config.set('Unproto', 'via', info.via)
        config.set_int('Unproto', 'port',
                       app.ports.port_for_index(info.port[0]))
        config.save_config()
        self._set_info()

    def _set_info(self):
        src = config.get('Unproto', 'source')
        if not src:
            src = config.get('Setup', 'callsign')
        dst = config.get('Unproto', 'destination')
        via = config.get('Unproto', 'via')
        text = "From: {}  To: {} ".format(src, dst)
        if via:
            # Vias are saved with spaces, but displayed with commas
            via = ','.join(via.split())
            text += " Via: {} ".format(via)
        self._menubar.status = text

    def _update_info(self, server):
        self._set_info()


# =============================================================================
# Startup
# =============================================================================

# This could use some explanation. The config and app vars are created at the
# top level so that they are accessible globally, without the need to use the
# 'global' keyword. The run() function exists to provide an entry point for
# use when the application is packaged as a zipapp. The usual __main__ form
# applies when running the code outside of a zipapp, during development.

config = config.Config('paracon_config')
config.load_config()
app = Application()


def run():
    app.run()


if __name__ == "__main__":
    run()
    
