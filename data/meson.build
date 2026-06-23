# --- Desktop entry ------------------------------------------------------------
desktop_file = i18n.merge_file(
  input: '@0@.desktop.in'.format(app_id),
  output: '@0@.desktop'.format(app_id),
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: datadir / 'applications',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

# --- AppStream metainfo -------------------------------------------------------
metainfo_file = i18n.merge_file(
  input: '@0@.metainfo.xml.in'.format(app_id),
  output: '@0@.metainfo.xml'.format(app_id),
  po_dir: '../po',
  install: true,
  install_dir: datadir / 'metainfo',
)

appstream_util = find_program('appstreamcli', required: false)
if appstream_util.found()
  test('Validate metainfo file', appstream_util,
    args: ['validate', '--no-net', '--explain', metainfo_file])
endif

# --- GSettings schema ---------------------------------------------------------
install_data(
  '@0@.gschema.xml'.format(app_id),
  install_dir: datadir / 'glib-2.0' / 'schemas',
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate GSettings schema', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()])
endif

# --- Icons --------------------------------------------------------------------
install_data(
  'icons/@0@.svg'.format(app_id),
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)
install_data(
  'icons/symbolic/@0@-symbolic.svg'.format(app_id),
  install_dir: datadir / 'icons' / 'hicolor' / 'symbolic' / 'apps',
)
# Raster icons: appstreamcli compose (run by flatpak-builder) needs a readable
# PNG, and Flathub requires one. Regenerate with build-aux/render-icon.py.
foreach size : ['128x128', '256x256']
  install_data(
    'icons' / size / '@0@.png'.format(app_id),
    install_dir: datadir / 'icons' / 'hicolor' / size / 'apps',
  )
endforeach

# --- Bundled catalog (offline fallback / first-run seed) ----------------------
install_data(
  '../catalog/manifest.json',
  install_dir: pkgdatadir / 'catalog',
)
install_data(
  '../catalog/schema.json',
  install_dir: pkgdatadir / 'catalog',
)
