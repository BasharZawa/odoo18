/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { registry } from "@web/core/registry";

import BpmnJS from 'https://unpkg.com/bpmn-js@11.5.0/dist/bpmn-modeler.development.js';

publicWidget.registry.BpmnEditor = publicWidget.Widget.extend({
    selector: '.oe_bpmn_editor',
    start: function () {
        const modeler = new BpmnJS({
            container: this.el
        });

        const xmlField = this.$el.closest("form").find("textarea[name='bpmn_xml']");

        const defaultXML = xmlField.val() || `
          <?xml version="1.0" encoding="UTF-8"?>
          <bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                            xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                            xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                            xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                            id="Definitions_1"
                            targetNamespace="http://bpmn.io/schema/bpmn">
            <bpmn:process id="Process_1" isExecutable="true">
              <bpmn:startEvent id="StartEvent_1"/>
            </bpmn:process>
            <bpmndi:BPMNDiagram id="BPMNDiagram_1">
              <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1"/>
            </bpmndi:BPMNDiagram>
          </bpmn:definitions>
        `;

        modeler.importXML(defaultXML).then(() => {
            const saveButton = document.createElement("button");
            saveButton.innerText = "Save Diagram";
            saveButton.className = "btn btn-primary mt-2";
            saveButton.onclick = async () => {
                const { xml } = await modeler.saveXML({ format: true });
                xmlField.val(xml).trigger('input');
                alert("Diagram saved to XML field.");
            };
            this.el.appendChild(saveButton);
        });
    }
});
