# =============================================================================
# Copyright (c) 2021-2024 Martin F N Cooper
#
# Author: Martin F N Cooper
# License: MIT License
# =============================================================================

"""
Application Configuration

Simple application configuration, providing for string, integer and boolean
values. A defaults file (.def) provides application defaults, while a user
config file (.cfg) provides user-specific values, falling back to the defaults
when not specified. A client can register a callback to be notified of changes
made particular sections of the config.
"""

import configparser
import importlib.resources
import pathlib


class Config:
    def __init__(self, fileroot, package=None):
        self.fileroot = fileroot
        self.package = package
        self.default_cfg = None
        self.user_cfg = None
        self.user_cfg_path = None
        self.callbacks = set()
        self.changed_sections = set()
        self.load_config()

    def find_user_config(self, cfg_file):
        if cfg_file:
            cfg_path = pathlib.Path(cfg_file)
            if cfg_path.exists():
                return cfg_path
        cfg_name = self.fileroot + '.cfg'
        cfg_path = pathlib.Path.cwd() / cfg_name
        if cfg_path.exists():
            return cfg_path
        cfg_path = pathlib.Path.home() / cfg_name
        if cfg_path.exists():
            return cfg_path
        return None

    def load_config(self, cfg_file=None):
        self.default_cfg = configparser.ConfigParser()
        if self.package:
            data = importlib.resources.read_text(
                self.package, self.fileroot + '.def')
            self.default_cfg.read_string(data)
        else:
            self.default_cfg.read(self.fileroot + '.def')

        self.user_cfg = configparser.ConfigParser()
        self.user_cfg_path = self.find_user_config(cfg_file)
        if self.user_cfg_path:
            self.user_cfg.read(self.user_cfg_path)
        self.changed_sections = set()

    def save_config(self):
        # Shorthand names for use in this method
        dcfg = self.default_cfg
        ucfg = self.user_cfg
        # Remove items from user config that are the same as defaults
        for section in ucfg.sections():
            for (key, val) in ucfg.items(section):
                if (dcfg.has_option(section, key)
                        and ucfg[section][key] == dcfg[section][key]):
                    ucfg.remove_option(section, key)
        # Save the updated user config
        cfg_path = (self.user_cfg_path
                    or pathlib.Path.cwd() / (self.fileroot + '.cfg'))
        with open(cfg_path, 'w') as f:
            ucfg.write(f)
        self.notify_all()
        self.changed_sections = set()

    def register(self, callback):
        self.callbacks.add(callback)

    def unregister(self, callback):
        self.callbacks.discard(callback)

    def notify_all(self):
        changes = frozenset(self.changed_sections)
        for callback in self.callbacks:
            callback(changes)

    def get(self, section, option):
        if self.user_cfg.has_option(section, option):
            return self.user_cfg[section][option]
        if self.default_cfg.has_option(section, option):
            return self.default_cfg[section][option]
        return None

    def get_int(self, section, option):
        val = self.get(section, option)
        return None if val is None else int(val)

    def get_bool(self, section, option):
        val = self.get(section, option)
        if val is None:
            return None
        if val:
            val = val.lower()
            if val in self.default_cfg.BOOLEAN_STATES:
                return self.default_cfg.BOOLEAN_STATES[val]
        return bool(val)

    def set(self, section, option, value):
        if not self.user_cfg.has_section(section):
            self.user_cfg.add_section(section)
        self.user_cfg[section][option] = value
        self.changed_sections.add(section)

    def set_int(self, section, option, value):
        if not isinstance(value, int):
            raise TypeError("option value must be int")
        self.set(section, option, str(value))
        self.changed_sections.add(section)

    def set_bool(self, section, option, value):
        if not isinstance(value, bool):
            raise TypeError("option value must be bool")
        self.set(section, option, 'true' if value else 'false')
        self.changed_sections.add(section)
