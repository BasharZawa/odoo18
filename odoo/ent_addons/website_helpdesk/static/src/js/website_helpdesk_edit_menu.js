/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { MenuDialog } from "@website/components/dialog/edit_menu";

/**
 * The goal of this patch is to prevent users from creating
 * website menu item with url of format /helpdesk/<team-slug>
 */
patch(MenuDialog.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.notification = useService('notification');
    },
    /**
     * @override
     */
    onClickOk() {
        if (this.url.isValid()) {
            const helpdesk_team_pattern = /^\/helpdesk\/([a-zA-Z]+-)+\d+$/;
            if (helpdesk_team_pattern.test(this.url.input.value)) {
                this.url.input.hasError = true;
                this.notification.add(
                    _t("The %s URL is reserved for the helpdesk team with the same name. \
                        To use it, please enable the 'website form' feature on that team instead.", this.url.input.value),
                    { type: 'danger' },
                );
                return;
            }
        }
        super.onClickOk();
    },
});
