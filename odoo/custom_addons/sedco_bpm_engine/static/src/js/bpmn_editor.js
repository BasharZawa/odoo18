import { registry } from "@web/core/registry";
import { Component, onMounted, useRef, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

// Use a local library placed under this module's static/lib for offline use.
// Serve module static files via Odoo's /web/static/<module>/... route
const LOCAL = "/web/static/sedco_bpm_engine/lib/bpmn-modeler.development.js";
const CDN   = "https://unpkg.com/bpmn-js@11/dist/bpmn-modeler.development.js";

class BpmnEditor extends Component {
  static template = xml/* xml */`
    <div class="o_bpmn_editor" style="border:1px solid #ddd; height:480px; position:relative;">
      <div class="o_bpmn_toolbar" style="position:absolute; top:6px; right:6px; z-index:2;">
        <button t-on-click="saveXml" type="button" class="btn btn-primary btn-sm">{{ _t('Save XML') }}</button>
        <button t-on-click="compileDef" type="button" class="btn btn-secondary btn-sm" style="margin-left:6px;">{{ _t('Compile to JSON') }}</button>
      </div>
      <div t-ref="canvas" style="width:100%; height:100%;"></div>
    </div>`;

  static props = {
    record: { type: Object },
    name: { type: String },
    value: { type: String, optional: true },
    readonly: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
  };

  setup() {
    this.canvas = useRef("canvas");
    this.notification = useService("notification");
    onMounted(async () => {
      await this._loadBpmn();
      await this._renderDiagram();
    });
  }

  async _loadBpmn() {
    if (window.BpmnJS) return;
    const tryLoad = (src) => new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src; s.onload = () => resolve(src); s.onerror = () => reject(src);
      document.head.appendChild(s);
    });
    try { await tryLoad(LOCAL); }
    catch (_) {
      try {
        this._warn(_t('Local bpmn-js not found. Trying CDN…'));
        await tryLoad(CDN);
      } catch (e) {
        this._error(_t('Failed to load bpmn-js. If your server is offline, download it to: ') + LOCAL);
      }
    }
  }

  async _renderDiagram() {
    if (!window.BpmnJS) return;
    this.modeler = new window.BpmnJS({ container: this.canvas.el });
    const xml = this.props.value || this._emptyXml();
    try {
      await this.modeler.importXML(xml);
      this._fitViewport();
    } catch (e) {
      this._error(_t('Failed to import BPMN XML: ') + (e?.message || e));
    }
  }

  _fitViewport() {
    try { this.modeler.get('canvas').zoom('fit-viewport', 'auto'); } catch(_){}
  }

  async saveXml() {
    if (!this.modeler) return this._error(_t('bpmn-js is not loaded.'));
    const { xml } = await this.modeler.saveXML({ format: true });
    const rec = this.props.record;
    if (!rec?.resModel || !rec?.resId) return this._error(_t('Record context missing. Save the record first.'));
    try {
      await rpc("/web/dataset/call_kw", {
        model: rec.resModel,
        method: "action_save_bpmn_xml",
        args: [[rec.resId], xml],
        kwargs: {},
      });
      // Update the field value in the form
      if (this.props.update) {
        await this.props.update(xml);
      }
      this._ok(_t('BPMN XML saved'));
    } catch (e) {
      this._error(_t('Save failed: ') + (e?.message || e));
    }
  }

  async compileDef() {
    if (!this.modeler) return this._error(_t('bpmn-js is not loaded.'));
    const { xml } = await this.modeler.saveXML({ format: true });
    const rec = this.props.record;
    if (!rec?.resModel || !rec?.resId) return this._error(_t('Record context missing. Save the record first.'));
    try {
      await rpc("/web/dataset/call_kw", {
        model: rec.resModel,
        method: "action_compile_bpmn_from_xml",
        args: [[rec.resId], xml],
        kwargs: {},
      });
      // Update the field value in the form
      if (this.props.update) {
        await this.props.update(xml);
      }
      this._ok(_t('Compiled BPMN to JSON'));
    } catch (e) {
      this._error(_t('Compile failed: ') + (e?.message || e));
    }
  }

  _emptyXml() {
    return [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
      ' xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"',
      ' xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"',
      ' xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"',
      ' xmlns:di="http://www.omg.org/spec/DD/20100524/DI"',
      ' xmlns:sedco="https://sedco.com/bpmn/extensions"',
      ' targetNamespace="http://bpmn.io/schema/bpmn">',
      '  <bpmn:process id="Process_1" isExecutable="true">',
      '    <bpmn:startEvent id="StartEvent_1" />',
      '  </bpmn:process>',
      '  <bpmndi:BPMNDiagram id="BPMNDiagram_1">',
      '    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1"/>',
      '  </bpmndi:BPMNDiagram>',
      '</bpmn:definitions>'
    ].join('');
  }

  _ok(msg)   { this.notification.add(msg,   { type: 'success' }); }
  _warn(msg) { this.notification.add(msg,   { type: 'warning' }); }
  _error(msg){ this.notification.add(msg,   { type: 'danger'  }); }
}

const fieldRegistry = registry.category("fields");
fieldRegistry.add("bpmn_editor", BpmnEditor);
export default BpmnEditor;
