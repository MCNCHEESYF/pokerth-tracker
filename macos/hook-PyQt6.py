# -----------------------------------------------------------------------------
# Copyright (c) 2005-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
# -----------------------------------------------------------------------------

"""
Hook for PyQt6 to ensure all necessary modules are included.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all PyQt6 submodules
hiddenimports = collect_submodules('PyQt6')

# Collect data files (plugins, Qt libraries, etc.)
datas = collect_data_files('PyQt6', include_py_files=False)
