# =============================================================================
# Copyright (c) 2021-2024 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Paracon Server

This provides a server API for the Paracon application that is intended to
be replaceable in a pluggable manner. This implementation is based on Packet
Engine, an implementation of the AGWPE protocol. A future implementation of
the same API may be constructed on top of the Linux AX.25 API (with suitable
changes to the Paracon GUI for configuration).
"""

from enum import Enum
import queue
import socket
import time

import pe.app
import pe.connect
import pe.monitor


class MonitorType(Enum):
    """
    Type used to identify records for the monitor, a 'listen'-like function
    built into Paracon.
    """
    UNPROTO_INFO   = 'UI'
    UNPROTO_OWN    = 'UO'
    UNPROTO_TEXT   = 'UT'
    UNPROTO_NETROM = 'UN'
    UNPROTO_BINARY = 'UB'
    CONN_INFO      = 'CI'
    CONN_TEXT      = 'CT'
    CONN_NETROM    = 'CN'
    CONN_BINARY    = 'CB'
    SUPER_INFO     = 'SI'


class _Monitor(pe.monitor.Monitor):
    """
    An implementation of the PE Monitor interface that places incoming data
    into a queue for consumption by the client, likely on a different thread.
    """

    def __init__(self):
        self._queue = queue.Queue()

    @property
    def event_queue(self):
        return self._queue

    def _monitored_unproto(self, port, call_from, call_to, text, data, own):
        mon_type = MonitorType.UNPROTO_OWN if own else MonitorType.UNPROTO_INFO
        self._queue.put((mon_type, port, text))
        if ' pid=F0 ' in text:
            self._queue.put((MonitorType.UNPROTO_TEXT, port,
                             data.decode('utf-8', 'replace')))
        elif ' pid=CF ' in text:
            self._queue.put((MonitorType.UNPROTO_NETROM, port, data))
        else:
            self._queue.put((MonitorType.UNPROTO_BINARY, port, data))

    def monitored_unproto(self, port, call_from, call_to, text, data):
        self._monitored_unproto(port, call_from, call_to, text, data, False)

    def monitored_own(self, port, call_from, call_to, text, data):
        self._monitored_unproto(port, call_from, call_to, text, data, True)

    def monitored_connected(self, port, call_from, call_to, text, data):
        self._queue.put((MonitorType.CONN_INFO, port, text))
        # Direwolf 1.6 has a bug whereby it prepends '0x' to the PID value
        # of 'I' frames only, so we need to work around that.
        if ' pid=F0 ' in text or ' pid=0xF0 ' in text:
            self._queue.put((MonitorType.CONN_TEXT, port,
                             data.decode('utf-8', 'replace')))
        elif ' pid=CF ' in text or ' pid=0xCF ' in text:
            self._queue.put((MonitorType.CONN_NETROM, port, data))
        else:
            self._queue.put((MonitorType.CONN_BINARY, port, data))

    def monitored_supervisory(self, port, call_from, call_to, text):
        self._queue.put((MonitorType.SUPER_INFO, port, text))


class _Connection(pe.connect.Connection):
    """
    An implementation of the PE Connection interface that, like the monitor,
    places incoming data into a queue for consumption by the client.
    """

    def __init__(self, port, call_from, call_to, incoming=False):
        super().__init__(port, call_from, call_to, incoming)
        self._queue = queue.Queue()

    @property
    def id(self):
        return self._key

    @property
    def event_queue(self):
        return self._queue

    def connected(self):
        self._queue.put(('status', 'connected'))

    def disconnected(self):
        if self.state is pe.connect.ConnectionState.TIMEDOUT:
            self._queue.put(('status', 'connect-timeout'))
        else:
            self._queue.put(('status', 'disconnected'))

    def data_received(self, pid, data):
        self._queue.put(('data', data))


class ServerError(Exception):
    def __init__(self, message, root):
        self.message = message
        self.root = root


class Server:
    """
    The server used by the Paracon application. This is a thin layer on top
    of the PE API, but serves to isolate the application from the concrete
    details of that API.
    """

    def __init__(self):
        self._engine = None
        self._monitor = None
        self._connection_queue = queue.Queue()
        self._active_connections = set()

    def start(self, host, port):
        self._engine = pe.app.Application()

        self._monitor = _Monitor()
        self._engine.use_monitor(self._monitor)

        try:
            self._engine.start(host, port)
        except socket.gaierror as e:
            if e.errno == socket.EAI_NONAME:
                msg = 'Server name not found'
            else:
                msg = 'Invalid server address'
            raise ServerError(msg, e)
        except ConnectionRefusedError as e:
            raise ServerError('Connection refused by server', e)
        except Exception as e:
            raise ServerError('Unknown server error', e)
        else:
            self._engine.enable_monitoring = True

    def stop(self):
        try:
            self._engine.enable_monitoring = False
        except BrokenPipeError:
            pass
        finally:
            self._engine.stop()

    def enable_debug(self, enable):
        self._engine.enable_debug_output = enable

    @property
    def ports(self):
        return self._engine.get_port_info()

    def register_callsign(self, callsign):
        if self._engine.is_callsign_registered(callsign):
            return True
        # Register and wait for completion
        self._engine.register_callsigns(callsign)
        wait = 20  # 2 seconds - quite a long time to wait
        while wait and not self._engine.is_callsign_registered(callsign):
            time.sleep(0.1)
            wait -= 1
        return self._engine.is_callsign_registered(callsign)

    def open_connection(self, port, call_from, call_to, via):
        conn = self._engine.open_connection(port, call_from, call_to, via)
        return conn

    def send_unproto(self, port, call_from, call_to, data, via):
        self._engine.send_unproto(port, call_from, call_to, data, via)

    @property
    def monitor_queue(self):
        return self._monitor.event_queue if self._monitor else None
