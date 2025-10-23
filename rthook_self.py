import sys
import types

# Create a mock module for 'self'
self_module = types.ModuleType('self')
sys.modules['self'] = self_module