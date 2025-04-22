import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { instanceofMarkup } from "@html_editor/utils/sanitize";
import { HtmlUpgradeManager } from "@knowledge/editor/html_migrations/html_upgrade_manager";
import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(HtmlViewer.prototype, {
    setup() {
        this.htmlUpgradeManager = this.env.htmlUpgradeManager || new HtmlUpgradeManager();
        // super setup is called after because it uses formatValue
        super.setup();
    },

    formatValue(value) {
        const newVal = this.htmlUpgradeManager.processForUpgrade(super.formatValue(value));
        if (instanceofMarkup(value)) {
            return markup(newVal);
        }
        return newVal;
    },
});
