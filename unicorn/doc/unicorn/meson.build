cdata = configuration_data()
cdata.set('VERSION', meson.project_version())

cdata.set('TOP_SRCDIR', meson.project_source_root())
cdata.set('DOCDIR', meson.current_source_dir())
cdata.set('DOCBUILDDIR', meson.project_build_root() / 'doc')

doxyfile = configure_file(
  input: 'Doxyfile.in',
  output: 'Doxyfile',
  configuration: cdata,
  install: false
)

unicorn_docs = custom_target(
  'unicorn-docs',
  input: doxyfile,
  output: 'html',
  command: [doxygen, doxyfile],
  depends: [hurricane_docs, viewer_docs, crlcore_docs],
  install: true,
  install_dir: docdir
)

