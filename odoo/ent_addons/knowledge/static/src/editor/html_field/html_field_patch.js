import { HtmlField } from "@html_editor/fields/html_field";
import { HtmlUpgradeManager } from "@knowledge/editor/html_migrations/html_upgrade_manager";
import { stripVersion } from "@knowledge/editor/html_migrations/manifest";
import { patch } from "@web/core/utils/patch";
import { markup, useSubEnv } from "@odoo/owl";
import { instanceofMarkup } from "@html_editor/utils/sanitize";

patch(HtmlField.prototype, {
    setup() {
        this.htmlUpgradeManager = new HtmlUpgradeManager();
        useSubEnv({
            htmlUpgradeManager: this.htmlUpgradeManager,
        });
        // super setup is called later because it uses this.value
        super.setup();
    },

    get value() {
        const value = super.value;
        const newVal = this.htmlUpgradeManager.processForUpgrade(value);
        if (instanceofMarkup(value)) {
            return markup(newVal);
        }
        return newVal;
    },

    clearElementToCompare(element) {
        super.clearElementToCompare(element);
        stripVersion(element);
    },
});
