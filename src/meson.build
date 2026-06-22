# Launcher script: configured from yonderloft.in, installed to bindir.
configure_file(
  input: 'yonderloft.in',
  output: 'yonderloft',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

# Inject build-time constants the package reads at runtime.
configure_file(
  input: 'yonderloft/_build.py.in',
  output: '_build.py',
  configuration: conf,
  install: true,
  install_dir: moduledir,
)

# Install the Python package under pkgdatadir (matches the launcher's sys.path).
install_subdir(
  'yonderloft',
  install_dir: pkgdatadir,
  exclude_files: ['_build.py.in'],
)
