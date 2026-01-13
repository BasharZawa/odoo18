/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

browser.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
        const btn = document.querySelector('button[name="action_scan_serial"]');
        if (btn) {
            btn.click();
        }
    }
});
