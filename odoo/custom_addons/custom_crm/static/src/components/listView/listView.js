/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class ListView extends Component {
    static template = "custom_crm.ListView";
    setup() { // constructor
        this.state = useState({ records: []        });
        this.orm = useService("orm");
        this.loadRecords(); 
    }

    
    // load records via ORM
    // async loadRecords() {
    //    const listViewService = await this.orm.searchRead("res.partner", 
    //     [
    //         ["is_company", "=", true],
    //     ], 
    //     [
    //         "id",
    //         "name", 
    //         "email",
    //         "phone",
    //         "country_id",
    //         "city",
    //         "street"
    //     ] 
    //    ); 
    //    this.state.records = listViewService;
    // }

    // load records via RPC
    async loadRecords(){
        const records = await rpc("/web/dataset/call_kw", {
            model: "res.partner",
            method: "search_read",
            args: [ []],
            kwargs: {
                fields: [
                    "id",
                    "name",
                    "email",
                    "phone",
                    "country_id",
                    "city",
                    "street"
                ],
            },
        });

        this.state.records = records;
    }

    async onCreateRecord() {
        const viewId = await rpc("/web/dataset/call_kw", {
            model: "ir.ui.view",
            method: "search",
            args: [[["name", "=", "res.partner.custom.custom.form"]]], // Replace with your view name
            kwargs: { limit: 1 },
        });
        
        debugger;

        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'form',
            target: 'current',
            views: [[viewId[0] || false, 'form']], // Use the fetched view ID or fallback to `false`
        });
    }
      


}

registry.category("actions").add("custom_crm.ListView", ListView, { force: true });

