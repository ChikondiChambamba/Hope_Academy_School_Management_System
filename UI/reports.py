"""UI wrapper module exposing `ReportsTab` for imports.

Some code imports `UI.reports` while the implementation lives in
`UI.reports_tab`. Provide a thin compatibility wrapper.
"""
from .reports_tab import ReportsTab

__all__ = ['ReportsTab']
