odoo.define('bpmn_engine.BpmnModelerWidget', function (require) {
    "use strict";
    const fieldRegistry = require('web.field_registry');
    const AbstractField = require('web.AbstractFieldOwl');

    class BpmnModelerWidget extends AbstractField {
        mounted() {
            super.mounted();
            this.modeler = new window.BpmnJS({container: this.el});
            if (this.value) {
                this.modeler.importXML(this.value);
            }
            this.modeler.on('commandStack.changed', () => {
                this.modeler.saveXML({format: true}).then(({xml}) => {
                    this._setValue(xml);
                });
            });
        }
        willUnmount() {
            if (this.modeler) {
                this.modeler.destroy();
            }
            super.willUnmount();
        }
    }
    fieldRegistry.add('bpmn_modeler', BpmnModelerWidget);
    return BpmnModelerWidget;
});
