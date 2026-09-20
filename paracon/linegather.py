# =============================================================================
# Copyright (c) 2021-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Line Gathering

Splits a stream of incoming byte chunks into lines, for display in a
terminal-like widget.
"""


class LineGatherer:
    """
    Splits a stream of incoming byte chunks into lines, tracking whether
    each line was terminated by an end-of-line sequence.

    Remote hosts commonly leave a final line - such as a login prompt -
    unterminated while they wait for a response, so a line is not held
    back until an EOL arrives. Instead, each call to feed() returns the
    unterminated tail (if any) as a non-final line, in addition to any
    complete lines found in the new data. That tail is re-emitted, with
    any further data appended, until it is eventually terminated.
    """
    def __init__(self):
        self._remains = b''
        self._skip_leading_lf = False

    def feed(self, data):
        # A chunk boundary can fall between the '\r' and '\n' of a single
        # CRLF sequence, since chunks are delivered as raw reads rather
        # than aligned to lines. Without this, the '\n' left over at the
        # start of the next chunk would be seen as its own line break,
        # producing a spurious blank line.
        if self._skip_leading_lf and data[:1] == b'\n':
            data = data[1:]
        if data:
            self._skip_leading_lf = data[-1:] == b'\r'
        # The text encodings we support all use the C0 control set, so it
        # is safe to identify line breaks before decoding. This allows
        # each line to be decoded independently, avoiding fragments of a
        # single line being decoded with different decoders.
        data = data.replace(b'\r\n', b'\r').replace(b'\n', b'\r')
        parts = data.split(b'\r')
        parts[0] = self._remains + parts[0]
        self._remains = parts.pop()
        lines = [(part, True) for part in parts]
        if self._remains:
            lines.append((self._remains, False))
        return lines

    def flush(self):
        """
        Force any buffered, unterminated bytes to be treated as a
        complete line. Used when the caller knows, by some means other
        than an EOL sequence, that no more data will extend the current
        line - for example, a remote host that does not itself echo
        input or emit a newline before its response.
        """
        remains = self._remains
        self._remains = b''
        self._skip_leading_lf = False
        return remains
