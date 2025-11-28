"""
Configuration Loader
====================

Centralized config loading. All thresholds from scanner_config.yaml.

Usage:
    from alpha_lab.config import get_config, cfg
    
    # Get specific value
    max_risk = get_config('account.risk_per_trade')
    
    # Get section
    extension = get_config('extension')
    
    # Direct access via cfg object
    from alpha_lab.config import cfg
    print(cfg.account.size)
"""

import os
import yaml
from typing import Any, Optional

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), 
    '../../configs/scanner_config.yaml'
)

_config = None


def load_config(path: str = None) -> dict:
    """Load configuration from YAML file."""
    global _config
    
    if _config is not None and path is None:
        return _config
    
    config_path = path or CONFIG_PATH
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            _config = yaml.safe_load(f)
    else:
        # Defaults if no config file
        _config = {
            'account': {'size': 100000, 'risk_per_trade': 500},
            'extension': {'hard_reject_5d': 20},
            'filters': {'min_price': 3, 'min_avg_volume': 500000},
        }
    
    return _config


def get_config(key: str, default: Any = None) -> Any:
    """
    Get config value by dot-notation key.
    
    Args:
        key: Dot-separated key like 'account.size' or 'extension.hard_reject_5d'
        default: Default value if key not found
    
    Returns:
        Config value or default
    """
    config = load_config()
    
    parts = key.split('.')
    value = config
    
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default
    
    return value


class ConfigNamespace:
    """Allows attribute-style access to config."""
    
    def __init__(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigNamespace(value))
            else:
                setattr(self, key, value)
    
    def __repr__(self):
        return f"ConfigNamespace({vars(self)})"


# Lazy-loaded config namespace
_cfg_namespace = None

def get_cfg() -> ConfigNamespace:
    """Get config as namespace for attribute access."""
    global _cfg_namespace
    if _cfg_namespace is None:
        _cfg_namespace = ConfigNamespace(load_config())
    return _cfg_namespace


# Convenience alias
cfg = property(lambda self: get_cfg())


# For direct import: from alpha_lab.config import cfg
class _ConfigProxy:
    """Proxy that loads config on first access."""
    def __getattr__(self, name):
        return getattr(get_cfg(), name)

cfg = _ConfigProxy()


if __name__ == "__main__":
    # Test config loading
    print("Config Test:")
    print(f"  Account size: {get_config('account.size')}")
    print(f"  Risk per trade: {get_config('account.risk_per_trade')}")
    print(f"  Extension reject: {get_config('extension.hard_reject_5d')}")
    print(f"  Min volume: {get_config('filters.min_avg_volume')}")
    
    # Test namespace
    c = get_cfg()
    print(f"\nNamespace test:")
    print(f"  c.account.size = {c.account.size}")
    print(f"  c.extension.hard_reject_5d = {c.extension.hard_reject_5d}")

