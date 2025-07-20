# =============================================================================
# Copyright (c) 2021-2025 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Urwid Extensions

A collection of widgets and utility functions that complement and enhance the
Urwid CUI library. Included are several higher-level widgets as well as some
functionality that could be considered "missing" from the base library.

These extensions require Python 3.7 or later.
"""

__author__ = 'Martin F N Cooper'
__version__ = '0.8.0'

import collections
from dataclasses import dataclass
from enum import Enum
import re
import time
from typing import Union

import urwid
import urwid.util


def auto_repr(cls):
    """
    Decorator to add automatic repr generation to a class. Simply apply the
    @auto_repr decorator to a class and a __repr__ function will be created.
    """
    def repr_fn(self):
        v = vars(self)
        kv = [item for k in v for item in (k, v[k])]
        f = ["{}={!r}"] * len(v)
        fs = "{}({})".format(self.__class__.__name__, ", ".join(f))
        return fs.format(*kv)
    setattr(cls, '__repr__', repr_fn)
    return cls


def safe_string(s):
    """
    Urwid interprets strings such that SO and SI are used to switch character
    encoding. This means they are not rendered at all, so here we replace them
    by their hex text equivalent.
    """
    if not isinstance(s, str):
        return s
    # Escape SO (Shift Out)
    s = '\\x0e'.join(s.split('\x0e'))
    # Escape SI (Shift In)
    s = '\\x0f'.join(s.split('\x0f'))
    return s


def safe_text(text):
    """
    Text can be constructed in several ways, viz a simple string; a tuple of
    attribute and string; or a list of either of those. This function invokes
    safe_string() on each string within the text item.
    """
    if isinstance(text, list):
        return [safe_text(item) for item in text]
    elif isinstance(text, tuple):
        return (text[0], safe_text(text[1]))
    return safe_string(text)


class _MouseDoublePressMapper:
    def __init__(self):
        self._last_mouse_press = 0

    def input_filter(self, keys, raw):
        """
        Synthesize mouse double-click events for left / middle / right mouse
        buttons. Less than 500ms between 2 clicks, with no other events in
        between constitute a double-click. The corresponding mouse release
        events are not modified; release events are generally not useful
        since they do not have accurate (or any) button information.
        """
        mod_keys = []
        for key in keys:
            last_press = 0
            if urwid.util.is_mouse_event(key):
                event, button, x, y = key
                if button <= 3:  # Ignore scroll events (4 and 5)
                    parts = event.split()
                    if parts[-1] == 'press':
                        now = time.time()
                        if now - self._last_mouse_press < 0.5:
                            ev = ' '.join(parts[:-2] + ['double'] + parts[-2:])
                            key = (ev, button, x, y)
                        last_press = now
                    elif parts[-1] == 'release':
                        last_press = self._last_mouse_press
            mod_keys.append(key)
            self._last_mouse_press = last_press
        return mod_keys


_mouse_double_press_mapper = _MouseDoublePressMapper()
mouse_double_press_filter = _mouse_double_press_mapper.input_filter


class DequeListWalker(collections.deque, urwid.ListWalker):
    """
    A clone of the Urwid SimpleListWalker class that uses a deque instead of
    a Monitored List. This is intended for widgets like long-lasting logs that
    could grow indefinitely. Using a deque allows placing an upper limit on
    the number of actual widgets retained in the list. In addition, since this
    is not intended as general purpose, append() is the only method captured
    as modifying the contents.
    """
    def __init__(self, contents, maxlen=200):
        collections.deque.__init__(self, contents, maxlen=maxlen)
        self.focus = 0

    @property
    def contents(self):
        return self

    def append(self, item):
        super().append(item)
        self._modified()

    def _modified(self):
        if self.focus >= len(self):
            self.focus = max(0, len(self) - 1)
        urwid.ListWalker._modified(self)

    def set_focus(self, position):
        try:
            if position < 0 or position >= len(self):
                raise ValueError
        except (TypeError, ValueError):
            raise IndexError("No widget at position %s" % (position,))
        self.focus = position
        self._modified()

    def next_position(self, position):
        if len(self) - 1 <= position:
            raise IndexError
        return position + 1

    def prev_position(self, position):
        if position <= 0:
            raise IndexError
        return position - 1

    def positions(self, reverse=False):
        if reverse:
            return range(len(self) - 1, -1, -1)
        return range(len(self))


class LoggingDequeListWalker(DequeListWalker):
    def __init__(self, contents, maxlen=200):
        self._logfile = None
        super().__init__(contents, maxlen)

    def set_logfile(self, filename):
        self._logfile = filename

    def append(self, item):
        super().append(item)
        if self._logfile:
            text = self._plain_text(item)
            if text == '' or text[-1] != '\n':
                text += '\n'
            with open(self._logfile, 'at', encoding='utf-8') as logfile:
                logfile.write(text)

    def _plain_text(self, text):
        if isinstance(text, list):
            return ''.join([self._plain_text(item) for item in text])
        elif isinstance(text, tuple):
            return self._plain_text(text[1])
        elif isinstance(text, urwid.AttrMap):
            return self._plain_text(text.original_widget)
        elif isinstance(text, urwid.Text):
            return text.text
        return text


class SelectableText(urwid.Text):
    """
    A Text subclass that allows the text to be selectable. This differs from
    the built-in SelectableIcon class in that it does not render a cursor.
    """
    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ActionableText(SelectableText):
    """
    A SelectableText subclass that emits a 'click' signal when the mouse is
    clicked on the text or when the 'enter' key is pressed while the text has
    focus.
    """
    signals = ['click']

    def keypress(self, size, key):
        if self._command_map[key] == urwid.ACTIVATE:
            self._emit('click')
            return None
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse press' and button == 1:
            self._emit('click')


class FilteringEdit(urwid.Edit):
    """
    An Edit subclass that may restrict or modify the characters allowed to
    be entered within the editable text field through the use of a filter
    provided by the client. If the filter returns None, the key is ignored.
    """
    def __init__(self, filter=None, **kwargs):
        self._filter = filter
        super().__init__(**kwargs)

    def keypress(self, size, key):
        if self._filter:
            key = self._filter(self, key)
        return super().keypress(size, key) if key is not None else None


class LineEntry(urwid.Edit):
    """
    An Edit subclass that emits a 'line_entry' signal when the 'enter' key is
    pressed. This is intended for single-line text entry, and will not work
    with multi-line widgets.
    """
    signals = ['line_entry']

    def keypress(self, size, key):
        if key is None:
            return
        key = super().keypress(size, key)
        if key != 'enter':
            return key
        text = self.get_edit_text().strip()
        self.set_edit_text("")
        self._emit('line_entry', text)


class Menu(urwid.WidgetWrap):
    """
    A horizontal menu of text items, each of which can be chosen using either
    the keyboard or the mouse. The items are specified by an Enum type, the
    values of which are used as the text for the items. Keyboard choice is
    using the meta key (usually Alt) with the first key of the Enum value.
    Mouse choice is by a click anywhere within the item text.

    Palette entries used:
        menu_key   -  the key used to invoke the menu item
        menu_text  -  the remainder of the item text
    """
    signals = ['select']

    @dataclass
    class MenuItem:
        member: Enum
        name: str
        key: str
        first: int
        last: int
        enabled: bool

    SPACING = 3

    def __init__(self, enum_type):
        self._items = []
        pos = 0
        for member in enum_type:
            name = member.value
            key = "meta {}".format(name[0].lower())
            self._items.append(self.MenuItem(
                member, name, key, pos, pos + len(name) - 1, True))
            pos += len(name) + self.SPACING
        self._text = urwid.Text(self._create_markup(self._items), 'left')
        super().__init__(self._text)

    def _create_markup(self, items):
        spaces = ' ' * self.SPACING
        menu = []
        for item in items:
            if item.enabled:
                menu.append(('menu_key', item.name[0]))
                menu.append(('menu_text', item.name[1:] + spaces))
            else:
                menu.append(('menu_text', item.name + spaces))
        return menu

    def enable(self, member, enabled):
        item = next(
            (i for i in self._items if i.member == member),
            None)
        if item and item.enabled != enabled:
            item.enabled = enabled
            self._text.set_text(self._create_markup(self._items))

    def keypress(self, size, key):
        item = next((i for i in self._items if i.key == key), None)
        if item and item.enabled:
            urwid.emit_signal(self, 'select', item.member)
            return None
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == 'mouse press' and button == 1:
            item = next(
                (i for i in self._items if col >= i.first and col <= i.last),
                None)
            if item and item.enabled:
                urwid.emit_signal(self, 'select', item.member)
                return True
        return False


class MenuBar(urwid.WidgetWrap):
    """
    A single-line widget containing a Menu on the left and an optional status
    Text item on the right.

    Palette entries used:
        menu_text  -  the status bar text
    """
    def __init__(self, menu_items, status=""):
        self._menu = Menu(menu_items)
        self._status = urwid.Text(status, 'right')
        widget = urwid.AttrMap(urwid.Padding(urwid.Columns([
            urwid.Filler(self._menu),
            urwid.Filler(self._status)
        ], box_columns=[0, 1]), left=1, right=1), 'menu_text')
        super().__init__(widget)

    @property
    def menu(self):
        return self._menu

    @property
    def status(self):
        return self._status.text

    @status.setter
    def status(self, text):
        self._status.set_text(text)

    def keypress(self, size, key):
        return self._menu.keypress(size, key)


class TabBar(urwid.WidgetWrap):
    """
    A single-line widget that comprises a set of tabs, generally used together
    with a set of box widgets to give the impression of a "notebook" or tabbed
    panel. Each tab has a name and is numbered with a single digit, such that
    it may be chosen by using the meta key (usually Alt) in conjunction with
    that digit. A tab may also be chosen by clicking on it with the mouse. A
    'select' signal is emitted when a tab is chosen. Tabs may be added or
    removed at will.

    Palette entries used:
        tabbar_sel    -  the currently selected tab
        tabbar_unsel  -  unselected tabs
    """
    signals = ['select']

    def __init__(self, items):
        self._items = items
        self._selected = 1
        self._text = urwid.Text(
            self._create_markup(self._items, self._selected))
        self._widget = urwid.AttrMap(urwid.Filler(self._text), 'tabbar_unsel')
        super().__init__(self._widget)

    def _create_markup(self, items, selected):
        tabs = ["  {}:{}  ".format(i + 1, j) for i, j in enumerate(items)]
        before = tabs[:selected - 1]
        after = tabs[selected:]
        before_text = (
            '│'.join(before) if len(before) > 1
            else (before[0] if len(before) else ''))
        after_text = (
            '│'.join(after) if len(after) > 1
            else (after[0] if len(after) else ''))
        markup = []
        if before_text:
            markup.append(('tabbar_unsel', before_text))
        markup.append(('tabbar_sel', tabs[selected - 1]))
        if after_text:
            markup.append(('tabbar_unsel', after_text))
        return markup

    def _refresh(self):
        self._text.set_text(self._create_markup(self._items, self._selected))

    def get_selected(self):
        return self._selected

    def set_selected(self, selected):
        if selected == self._selected:
            return
        # If old item has been removed, pass None instead of the item
        old_item = (self._items[self._selected - 1]
                    if self._selected < len(self._items) else None)
        old = (self._selected, old_item)
        new = (selected, self._items[selected - 1])
        self._selected = selected
        self._refresh()
        urwid.emit_signal(self, 'select', old, new)

    def get_tab_name(self, pos):
        if pos < 1 or pos > len(self._items):
            return ''
        return self._items[pos - 1]

    def set_tab_name(self, pos, name):
        if pos < 1 or pos > len(self._items):
            return
        self._items[pos - 1] = name
        self._refresh()

    def add_tab(self, name):
        if len(self._items) >= 9:
            return 0
        self._items.append(name)
        self._refresh()
        return len(self._items)

    def remove_tab(self, pos):
        if pos < 1 or pos > len(self._items) or len(self._items) == 1:
            return
        if pos == self._selected:
            selected = 1  # Maybe go to previous instead?
        elif pos < self._selected:
            selected = self._selected - 1
        else:
            selected = self._selected
        del self._items[pos - 1]
        self.set_selected(selected)
        self._refresh()

    def keypress(self, size, key):
        parts = key.split()
        if len(parts) != 2 or len(parts[1]) != 1 or not parts[1].isdigit():
            return key
        pos = int(parts[1])
        if pos < 1 or pos > len(self._items):
            return key
        self.set_selected(pos)
        return None

    def mouse_event(self, size, event, button, col, row, focus):
        if event != 'mouse press' or button != 1:
            return False
        text = self._text.text
        if col < len(text) and text[col] != '│':
            items = re.findall(r"  \d:\w+  ", text.replace('|', ''))
            for item in reversed(items):
                if col >= text.index(item):
                    self.set_selected(int(item[2]))
                    return True
        return False


class _DropdownListBox(urwid.ListBox):
    signals = ['select']

    def keypress(self, size, key):
        if key == 'enter':
            self._emit('select', self.focus_position)
        elif key == 'esc':
            self._emit('select', -1)
        else:
            return super().keypress(size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        # Allow focus change to happen first
        result = super().mouse_event(size, event, button, col, row, focus)
        if event == 'mouse press' and button == 1:
            self._emit('select', self.focus_position)
            return True
        return result


class Dropdown(urwid.PopUpLauncher):
    """
    A drop-down list of items that displays the currently selected item when
    closed and, in addition, the list of available items when open. The list
    may be opened either by a mouse click or with the 'enter' key when the
    widget has focus. Selecting an item will close the list, or the list may
    be closed without changing the selection using the 'esc' key.

    Palette entries used:
        dropdown_sel   -  the current drop-down selection
        dropdown_item  -  an item in the open drop-down list
    """
    def __init__(self, items, caption=None, default=None):
        self._items = items

        # Ensure a usable default
        initial_pos = 0
        if default is not None:
            if type(default) is str:
                if default in items:
                    initial_pos = items.index(default)
            elif default >= 0 and default < len(items):
                initial_pos = default
        self._selection = initial_pos

        # Calculate popup size
        self._offset = len(caption) if caption is not None else 0
        self._width = max([len(i) for i in self._items]) + 4
        self._height = len(self._items) + 2

        # Create the popup up front
        entries = [
            urwid.AttrMap(urwid.Padding(
                ActionableText(item), left=1, right=1),
                'dropdown_item', 'dropdown_sel')
            for item in items]
        self._listbox = _DropdownListBox(urwid.SimpleFocusListWalker(entries))
        self._listbox.set_focus(initial_pos)
        urwid.connect_signal(self._listbox, 'select', self._item_selected)
        self._popup = urwid.AttrMap(
            urwid.LineBox(self._listbox), 'dropdown_item')

        # The caption
        self._caption_text = urwid.Text(caption)

        # Now the clickable text that pops up the dropdown
        self._trigger_text = ActionableText(
            self._make_trigger_text(initial_pos))
        urwid.connect_signal(
            self._trigger_text, 'click', lambda w: self.open_pop_up())

        # And finally the dropdown widget itself
        self._dropdown = urwid.Columns([
            (len(caption), self._caption_text),
            urwid.AttrMap(self._trigger_text, 'dropdown_item', 'dropdown_sel')
        ])
        super().__init__(self._dropdown)

    def create_pop_up(self):
        return self._popup

    def get_pop_up_parameters(self):
        return {
            'left': self._offset, 'top': 0,
            'overlay_width': self._width, 'overlay_height': self._height
        }

    def _make_trigger_text(self, pos):
        return "\u2193 " + self._items[pos]

    def _item_selected(self, w, pos):
        if pos >= 0:
            self._selection = pos
            self._trigger_text.set_text(self._make_trigger_text(pos))
        self.close_pop_up()

    def get_selection(self):
        return (self._selection, self._items[self._selection])

    def set_caption(self, caption):
        contents = self._dropdown.contents
        self._caption_text.set_text(caption)
        contents[0] = (
            self._caption_text,
            urwid.Columns.options('given', len(caption), False))


class ButtonSet(urwid.WidgetWrap, urwid.WidgetContainerMixin):
    """
    A set of buttons rendered sequentially in a single row. Typically used as
    action buttons in a dialog. When a button is chosen, either by a mouse
    click or with the 'enter' key, a 'click' signal is emitted with the button
    index as the data argument.

    Palette entries used:
        button_select  -  selectable button
        button_focus   -  currently selected button
    """
    def __init__(self, labels):
        maxlen = max([len(label) for label in labels]) + 4
        buttons = []
        for ix, label in enumerate(labels):
            button = urwid.Button(label)
            button._label.align = 'center'
            urwid.connect_signal(button, 'click', self._callback, ix)
            buttons.append(
                urwid.AttrMap(button, 'button_select', 'button_focus'))
        button_set = urwid.Columns(
            [(maxlen, b) for b in buttons], dividechars=2)
        self._button_set = button_set
        self._total_width = (maxlen + 2) * len(labels) - 2
        urwid.register_signal(ButtonSet, ['click'])
        super().__init__(button_set)

    def _callback(self, button, index):
        urwid.emit_signal(self, 'click', index)

    @property
    def width(self):
        return self._total_width

    # The following methods are required for a widget to behave properly as
    # a container subclassing WidgetContainerMixin, and in particular to
    # participate in the focus chain. This fact is not documented in Urwid,
    # but determined by reviewing its own container implementations.

    @property
    def contents(self):
        return self._button_set.contents

    @property
    def focus(self):
        return self._button_set.focus

    @focus.setter
    def focus(self, item):
        self._button_set.focus = item

    @property
    def focus_position(self):
        return self._button_set.focus_position

    @focus_position.setter
    def focus_position(self, position):
        self._button_set.focus_position = position

    # These two methods are taken from WidgetContainerListContentsMixin, which
    # is not public, for some reason.

    def __iter__(self):
        return iter(range(len(self.contents)))

    def __reversed__(self):
        return iter(range(len(self.contents) - 1, -1, -1))


class _ModalExit(Exception):
    def __init__(self, index):
        self.index = index


class Dialog(metaclass=urwid.MetaSignals):
    """
    A base class for modal or modeless dialogs. Subclasses must implement the
    get_body() method to provide the widgets that will be added to a 'pile' in
    between the provided title and button set. Whether the dialog is modal or
    modeless is determined by the 'modal' boolean argument to show(), with the
    default being modeless.

    Palette entries used:
        dialog_back    -  background for dialog
        dialog_header  -  title bar at top of dialog
    """
    signals = ['dialog_button']

    def __init__(self, title, buttons, escape=None):
        self._title = title
        self._buttons = buttons
        if escape is not None and type(escape) is int:
            self._escape = buttons[int(escape)]
        else:
            self._escape = escape
        self._layout = None
        self._focus_paths = []
        self._loop = None
        self._loop_widget = None
        self._overlay_keypress = None
        self._waiting_for_close = False

    def _create_header(self):
        return urwid.AttrMap(
            urwid.Text(self._title, 'center'), 'dialog_header')

    def _create_footer(self):
        buttons = ButtonSet(self._buttons)
        urwid.connect_signal(buttons, 'click', self._callback)
        return urwid.Padding(buttons, width=buttons.width, align='center')

    def _create_layout(self):
        layout = urwid.Pile([
            self._create_header(),
            ('weight', 1, self.get_body()),
            self._create_footer()
        ])
        return layout

    def get_body(self):
        raise NotImplementedError('Dialog subclass must implement get_body()')

    def _build_focus_paths(self, widget, path, result):
        widget = widget.base_widget
        if not isinstance(widget, urwid.WidgetContainerMixin):
            return result.append(path)
        for i, (w, _) in enumerate(widget.contents):
            if (isinstance(w.base_widget, urwid.Widget)
                    and w.base_widget.selectable()):
                self._build_focus_paths(
                    widget.contents[i][0], [*path, i], result)

    def show(self, loop, modal=False):
        self._loop = loop
        self._loop_widget = loop.widget

        self._layout = self._create_layout()
        self._build_focus_paths(self._layout, [], self._focus_paths)

        dlg = urwid.Overlay(
            urwid.AttrMap(urwid.LineBox(self._layout), 'dialog_back'),
            self._loop_widget,
            width=46, height='pack',
            align='center', valign='middle')

        self._overlay_keypress = dlg.keypress
        dlg.keypress = self._keypress

        self._loop.widget = dlg

        if modal:
            self._wait_modal()

    def _wait_modal(self):
        self._waiting_for_close = True
        while self._waiting_for_close:
            try:
                # In order to wait until the dialog is closed, we need to take
                # over the event loop, so that events will continue to be
                # processed in the normal way until we are ready to exit.
                event_loop = self._loop.event_loop
                event_loop._did_something = True
                while True:
                    event_loop._loop()
            except _ModalExit as e:
                close = urwid.emit_signal(self, 'dialog_button', e.index)
                if close:
                    self._loop.widget = self._loop_widget
                    self._loop_widget._invalidate()
                    self._waiting_for_close = False

    def _exit_modal(self, loop, index):
        # Using an alarm gets this callback invoked inside the event loop,
        # and raising an exception allows us to break out of that loop. We
        # pass on the button index for processing the actual dialog exit.
        raise _ModalExit(index)

    def _callback(self, index):
        if self._waiting_for_close:
            self._loop.set_alarm_in(0, self._exit_modal, index)
        else:
            close = urwid.emit_signal(self, 'dialog_button', index)
            if close:
                self._loop.widget = self._loop_widget
                self._loop_widget._invalidate()

    def _keypress(self, size, key):
        if (self._escape is not None and self._escape in self._buttons
                and type(key) is str and key == 'esc'):
            self._callback(self._buttons.index(self._escape))
            return None
        if type(key) is str and key in ('tab', 'shift tab'):
            self._change_focus(key)
            return None
        return self._overlay_keypress(size, key)

    def _change_focus(self, key):
        cur_path = self._layout.get_focus_path()
        cur_index = self._focus_paths.index(cur_path)
        if key == 'tab':
            new_index = (cur_index + 1) % len(self._focus_paths)
        else:
            new_index = (cur_index - 1) % len(self._focus_paths)
        self._layout.set_focus_path(self._focus_paths[new_index])


class FormDialog(Dialog):
    """
    A Dialog subclass specifically designed for forms. Fields are added from
    the subclass by implementing add_fields(). Supported field types are
    string, int and dropdown, added through corresponding methods. Groups of
    fields are supported, and are rendered as separate boxes with a label.
    A subclass may optionally implement the validate() method, which should
    return None on success and an error to be displayed on failure. The
    optional save() method is called when validation succeeds.

    Palette entries used:
        field_error  -  error message when field is invalid
    """

    @dataclass
    class FormField:
        name: str
        label: str
        widget: urwid.Widget
        value: Union[int, str]
        group: str

    def __init__(self, title):
        super().__init__(title, ['Okay', 'Cancel'], 1)
        urwid.connect_signal(self, 'dialog_button', self._button_pressed)
        self.groups = {}
        self.fields = []

    def add_fields(self):
        raise NotImplementedError(
            'FormDialog subclass must implement add_fields()')

    def add_group(self, name, label=None):
        self.groups[name] = label

    def add_edit_str_field(
            self, name, label, value='', group=None, filter=None):
        caption = "{}: ".format(label)
        widget = FilteringEdit(caption=caption, edit_text=value, filter=filter)
        urwid.connect_signal(widget, 'change', self._field_changed)
        self.fields.append(self.FormField(name, label, widget, value, group))

    def get_edit_str_value(self, name):
        field = next((f for f in self.fields if f.name == name), None)
        return field.widget.edit_text if field else None

    def add_edit_int_field(self, name, label, value=None, group=None):
        caption = "{}: ".format(label)
        widget = urwid.IntEdit(caption=caption, default=value)
        urwid.connect_signal(widget, 'change', self._field_changed)
        self.fields.append(self.FormField(name, label, widget, value, group))

    def get_edit_int_value(self, name):
        field = next((f for f in self.fields if f.name == name), None)
        return field.widget.value() if field else None

    def add_dropdown_field(
            self, name, label, values=[], initial=0, group=None):
        caption = "{}: ".format(label)
        widget = Dropdown(values, caption, initial)
        self.fields.append(self.FormField(name, label, widget, values, group))

    def get_dropdown_value(self, name):
        field = next((f for f in self.fields if f.name == name), None)
        return field.widget.get_selection()

    def get_body(self):
        self.add_fields()
        self._adjust_captions()
        current_group = None
        group_widgets = []
        pile_widgets = []
        for f in self.fields:
            if f.group == current_group:
                # Add to current group
                group_widgets.append(f.widget)
            else:
                # New group - if old one was not empty, output widgets
                if group_widgets:
                    if len(group_widgets) == 1:
                        pile_widgets.append(urwid.LineBox(
                            group_widgets[0],
                            title=self.groups[current_group]))
                    else:
                        pile_widgets.append(urwid.LineBox(
                            urwid.Pile(group_widgets),
                            title=self.groups[current_group]))
                group_widgets = []
                current_group = f.group
                group_widgets.append(f.widget)
        if group_widgets:
            box_title = (
                '' if current_group is None else self.groups[current_group])
            if len(group_widgets) == 1:
                pile_widgets.append(urwid.LineBox(
                    group_widgets[0],
                    title=box_title))
            else:
                pile_widgets.append(urwid.LineBox(
                    urwid.Pile(group_widgets),
                    title=box_title))
        self._error = urwid.Text(('field_error', ""), align='center')
        pile_widgets.append(self._error)
        self._body = urwid.Pile(pile_widgets)
        return self._body

    def _adjust_captions(self):
        # Calculate max caption length for each group
        widths = {}
        for field in self.fields:
            label_len = len(field.label)
            if field.group not in widths or label_len > widths[field.group]:
                widths[field.group] = label_len
        # Now adjust the field captions
        for field in self.fields:
            label_len = len(field.label)
            group_width = widths[field.group]
            if label_len < group_width:
                field.widget.set_caption("{}:{}".format(
                    field.label, ' ' * (group_width - label_len + 1)))

    def validate(self):
        return None

    def save(self):
        pass

    def _field_changed(self, widget, text):
        self._error.set_text("")

    def _button_pressed(self, index):
        if index == 0:
            message = self.validate()
            if message:
                self._error.set_text(('field_error', message))
                return False
            self.save()
        return True
