/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";

export class BpmnEditor extends Component {
    setup() {
        onMounted(async () => {
            const BpmnJS = window.BpmnJS;
            this.modeler = new BpmnJS({ container: this.refs.canvas });

            // Load initial BPMN from hidden textarea
            const xmlField = this.el.querySelector("textarea[name='bpmn_xml']");
            const initialXml = xmlField?.value || this.defaultXml();

            try {
                await this.modeler.importXML(initialXml);
            } catch (err) {
                console.error("BPMN load error", err);
            }

            const saveBtn = document.createElement("button");
            saveBtn.innerText = "Save BPMN";
            saveBtn.className = "btn btn-sm btn-primary mt-2";
            saveBtn.onclick = async () => {
                const { xml } = await this.modeler.saveXML({ format: true });
                xmlField.value = xml;
                xmlField.dispatchEvent(new Event("input"));
                alert("BPMN saved");
            };
            this.refs.controls.appendChild(saveBtn);
        });
    }

    defaultXml() {
        return `<?xml version="1.0" encoding="UTF-8"?>
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
</bpmn:definitions>`;
    }
}

BpmnEditor.template = "bpm_engine.BpmnEditor";
