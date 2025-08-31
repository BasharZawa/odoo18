
Place a compatible bpmn-js modeler build file named `bpmn-modeler.development.js` in this directory.

Recommended version: 11.x (tested) or 8.x stable builds.

Example download command (run from repository root):

curl -L -o odoo/custom_addons/sedco_bpm_engine/static/lib/bpmn-modeler.development.js \
  https://unpkg.com/bpmn-js@11.5.0/dist/bpmn-modeler.development.js

After placing the file, update the module and restart Odoo so the file is served at:
  /web/static/sedco_bpm_engine/lib/bpmn-modeler.development.js

