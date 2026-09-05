# -*- coding: utf-8 -*-
"""
G10 adapters package init
"""
from .base_adapter import BaseReportAdapter
from .datagov_adapter import DataGovAdapter

__all__ = ["BaseReportAdapter", "DataGovAdapter"]
