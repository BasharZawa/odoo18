/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { onMounted } from "@odoo/owl";

export class FieldBpmnEditor extends CharField {
    setup() {
        super.setup();
        onMounted(this.initBpmn);
    }

    async initBpmn() {
        const BpmnJS = window.BpmnJS;
        const container = this.el.querySelector(".bpmn-canvas");

        this.modeler = new BpmnJS({ container });

        const initialXml = this.props.value || this.defaultXml();

        try {
            await this.modeler.importXML(initialXml);
        } catch (err) {
            console.error("Error loading BPMN XML:", err);
        }

        const saveBtn = document.createElement("button");
        saveBtn.innerText = "Save BPMN";
        saveBtn.className = "btn btn-primary mt-2";
        saveBtn.onclick = async () => {
            const { xml } = await this.modeler.saveXML({ format: true });
            this.props.update(xml);  // saves to field
        };
        this.el.appendChild(saveBtn);
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

    render() {
        this.el.innerHTML = `
            <div class="bpmn-canvas" style="height: 500px; border: 1px solid #ccc;"></div>
        `;
    }
}

registry.category("fields").add("bpmn_editor", FieldBpmnEditor);
