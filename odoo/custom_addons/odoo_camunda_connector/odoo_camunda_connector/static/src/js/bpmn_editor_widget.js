/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { useDebounced } from "@web/core/utils/timing";
import { useExternalListener } from "@web/core/utils/hooks";

const { Component, onMounted, onWillUnmount, onWillUpdateProps, useRef, useState } = owl;

// Import bpmn-js library (assuming it's loaded globally or via assets)
// In a real scenario, you might need a more robust way to import if using ES modules
const BpmnJS = window.BpmnJS;

export class BpmnEditorWidget extends Component {
    static template = "odoo_camunda_connector.BpmnEditorWidget";
    static components = {};
    static props = {
        ...CharField.props,
        // Add any custom props if needed
    };

    setup() {
        this.bpmnContainerRef = useRef("bpmnContainer");
        this.bpmnModeler = null;
        this.initialXml = this.props.record.data[this.props.name] || "";
        this.currentXml = this.initialXml;
        this.state = useState({ isLoading: true });

        // Debounce the update function to avoid too frequent updates
        this.debouncedUpdate = useDebounced(this.updateValue, 300);

        onMounted(() => {
            this.initializeBpmnEditor();
            // Add listener for window resize to potentially adjust editor size
            useExternalListener(window, "resize", this.onResize);
        });

        onWillUpdateProps(async (nextProps) => {
            const newXml = nextProps.record.data[nextProps.name] || "";
            if (this.bpmnModeler && newXml !== this.currentXml) {
                _logger.info("BPMN Editor: Props updated, reloading XML");
                this.initialXml = newXml;
                this.currentXml = newXml;
                await this.loadDiagram(newXml);
            }
        });

        onWillUnmount(() => {
            if (this.bpmnModeler) {
                this.bpmnModeler.destroy();
                this.bpmnModeler = null;
                _logger.info("BPMN Editor: Destroyed");
            }
        });
    }

    async initializeBpmnEditor() {
        if (!BpmnJS) {
            console.error("BpmnJS library not loaded!");
            this.state.isLoading = false;
            return;
        }
        if (!this.bpmnContainerRef.el) {
            console.error("BPMN container element not found!");
            this.state.isLoading = false;
            return;
        }

        _logger.info("BPMN Editor: Initializing...");
        this.state.isLoading = true;
        try {
            this.bpmnModeler = new BpmnJS({
                container: this.bpmnContainerRef.el,
                height: "600px", // Make this dynamic or configurable?
                keyboard: {
                    bindTo: window
                },
                // Add any other bpmn-js options here
                // propertiesPanel: { // Example if using properties panel
                //   parent: "#js-properties-panel"
                // }
            });

            // Event listener for changes in the diagram
            this.bpmnModeler.on("commandStack.changed", this.onDiagramChange);

            await this.loadDiagram(this.initialXml);
            _logger.info("BPMN Editor: Initialized successfully.");

        } catch (err) {
            console.error("Error initializing BPMN Modeler:", err);
            _logger.error("Error initializing BPMN Modeler: ", err);
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadDiagram(xml) {
        const emptyDiagram = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" x="173" y="102" width="36" height="36"/>
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;
        
        const diagramXml = xml || emptyDiagram;

        try {
            if (this.bpmnModeler) {
                await this.bpmnModeler.importXML(diagramXml);
                this.fitViewport();
                _logger.info("BPMN Editor: Diagram loaded.");
            }
        } catch (err) {
            console.error("Error loading BPMN XML:", err);
            _logger.error("Error loading BPMN XML: ", err);
            // Optionally load the empty diagram on error?
            // await this.bpmnModeler.importXML(emptyDiagram);
            // this.fitViewport();
        }
    }

    onDiagramChange = async () => {
        _logger.debug("BPMN Editor: Diagram changed.");
        if (this.bpmnModeler) {
            try {
                const { xml } = await this.bpmnModeler.saveXML({ format: true });
                this.currentXml = xml;
                this.debouncedUpdate(); // Call debounced update
            } catch (err) {
                console.error("Error saving BPMN XML:", err);
                _logger.error("Error saving BPMN XML: ", err);
            }
        }
    };

    updateValue() {
        _logger.debug("BPMN Editor: Updating record value.");
        this.props.record.update({ [this.props.name]: this.currentXml });
    }

    fitViewport() {
        if (this.bpmnModeler) {
            const canvas = this.bpmnModeler.get("canvas");
            canvas.zoom("fit-viewport", "auto");
        }
    }

    onResize = () => {
        // Basic resize handling, might need debouncing
        if (this.bpmnModeler) {
           // Currently bpmn-js doesn't auto-resize well with just CSS
           // We might need to destroy and re-initialize or find another way
           // For now, just log it.
           _logger.debug("Window resized, BPMN editor might need manual adjustment or re-render.");
        }
    };
}

registry.category("fields").add("bpmn_editor", {
    component: BpmnEditorWidget,
    displayName: "BPMN Editor",
    supportedTypes: ["text"],
    // Add other configurations if needed
});

