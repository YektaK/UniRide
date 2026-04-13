#!/usr/bin/env python
"""Verify all strategies in registry"""

import sys
sys.path.insert(0, '.')

from strategies import STRATEGY_REGISTRY, get_strategy_info

print('📋 STRATEJİ REGISTRY')
print('=' * 60)
for name, strategy in STRATEGY_REGISTRY.items():
    print(f'{name:20} -> {strategy.display_name}')

print()
print('📊 BENZERSİZ STRATEJİLER')
print('=' * 60)
for info in get_strategy_info():
    print(f"• {info['name']:15} : {info['display_name']}")
    print(f"  {info['description']}")
    print()
