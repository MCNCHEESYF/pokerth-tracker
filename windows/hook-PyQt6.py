# -----------------------------------------------------------------------------
# Hook for PyQt6 to ensure all necessary modules are included.
# -----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all PyQt6 submodules
hiddenimports = collect_submodules('PyQt6')

# Collect data files (plugins, Qt libraries, etc.)
datas = collect_data_files('PyQt6', include_py_files=False)
