# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
"""
Workspace management module for the DeepDiver Multi-Agent System.

This module provides local workspace management capabilities that don't require
external dependencies like E2B. Each chat session gets its own isolated workspace
directory for file operations and data persistence.
"""

from .local_workspace_manager import (
    LocalWorkspaceManager,
    WorkspaceInfo,
    WorkspaceStatus,
    get_workspace_manager,
    initialize_workspace_manager,
    shutdown_workspace_manager
)

__all__ = [
    'LocalWorkspaceManager',
    'WorkspaceInfo',
    'WorkspaceStatus',
    'get_workspace_manager',
    'initialize_workspace_manager',
    'shutdown_workspace_manager'
]
