project('yonderloft',
  version: '0.1.0',
  license: 'GPL-3.0-or-later',
  meson_version: '>= 0.62.0',
)

# --- Identity -----------------------------------------------------------------
app_id = 'uk.aaronworld.Yonderloft'

# --- Tooling ------------------------------------------------------------------
python = import('python').find_installation('python3')
gnome = import('gnome')
i18n = import('i18n')

dependency('glib-2.0', version: '>= 2.74')
dependency('gtk4', version: '>= 4.10')
# 1.5 for AdwDialog / AdwAlertDialog / AdwAboutDialog.
dependency('libadwaita-1', version: '>= 1.5')

# --- Paths --------------------------------------------------------------------
prefix = get_option('prefix')
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')
pkgdatadir = datadir / meson.project_name()
moduledir = pkgdatadir / 'yonderloft'

# --- Configuration injected into the package ----------------------------------
conf = configuration_data()
conf.set('APP_ID', app_id)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python.full_path())
conf.set('pkgdatadir', pkgdatadir)
conf.set('localedir', prefix / get_option('localedir'))

subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
