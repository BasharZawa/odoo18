from odoo import models
import requests
import logging
from datetime import datetime
from odoo import fields
import json





class AccountMove(models.Model):

    _inherit = "account.move"



    def action_post(self):
        # Call the original post method (invoice validation)
        res = super(AccountMove, self).action_post()

        for move in self:
            if move.state == 'posted' and move.move_type in ['out_invoice', 'out_refund']:  # Only customer invoices/credit notes
                self._send_invoice_to_api(move)


        return res

    def _send_invoice_to_api(self, move):
        """Prepare and send invoice data to external API"""



        url = (
            "https://dev.orchida-einvoice.com/api-pub/api/InvGenerateQr"
        )



        token = self.env['ir.config_parameter'].sudo().get_param('api_module.api_token')
        comapany_id = self.env['ir.config_parameter'].sudo().get_param('CompanyID')





        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Company-id" :comapany_id,


        }

        params = {
            "Format": "integrator",

        }


        payload = {
            "internalCode":  move.name , #invoice number
            "type": "i",                  # standart.. credit ..debit
            "dateTimeIssued": move.invoice_date and move.invoice_date.strftime("%Y-%m-%dT%H:%M") or datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "buyerCode": "1",
            "currency": move.currency_id.name ,
            "currRate": move.currency_id._get_conversion_rate(
                move.currency_id, move.company_id.currency_id, move.company_id, move.invoice_date or fields.Date.today()
             ),
            "note": move.narration or "",
            "refCode": "",  # refrence standart invoice (c,d)
            "total": move.amount_total,
            "prepaid": "0", ######
            "OrderReferenceID": "",#(#not mandatory)
            "SalesOrderID": "",
            "rounding": 0,   #(not mandatory)
            "buyerEndpointID": "100820361200003",
            "buyerSchemeID": "0235",
            "buyerName": "buyerTest",
            "buyerStreet": "62 dubai st",
            "buyerCity": "Dubai",
            "buyerSubentity": "AUH",
            "buyerCountry": "AE",
            "buyerTaxID": "100820361200003",
            "buyerType": "TRN",
            "buyerAgencyID": "TL",
            "buyerAgencyName": "Orchida Soft",
            "allowances": [
                {
                    "Indicator": "false",
                    "ReasonCode": "95",
                    "Reason": "Damaged Goods Discount",
                    "Amount": "280",
                    "TaxCatID": "S",
                    "TaxPercent": "5",
                    "ExemptionCode": "",
                    "ExemptionReason": ""
                }
            ],
            "PaymentMeans": [
                {
                    "Name": "card",
                    "Code": "10",
                    "networkID": "",
                    "holderName": ""

                }
            ],
            "lines": [],
        }


        for line in move.invoice_line_ids:
            payload["lines"].append({
                "Description": line.name or line.product_id.display_name or "",
                "Name": line.product_id.name or "Unknown",
                "itemCode": str(line.product_id.id or 0),
                "buyerItemCode": "bx0023",
                "Note": "",
                "itemDiscountAmount": 0,
                "Quantity": line.quantity,
                "UnitValue": line.price_unit,
                "UnitCode": "",  # Default unit
                "lineVATRate": 0,
                "lineVATSubtype": "",
                "lineVATReason": "",
                "lineVATReasonDesc": "",
            })





        data = {
            "payload": payload,
            "headers": headers
        }


        with open("request_data.json", "w") as f:
            json.dump(data, f, indent=4)

        response = requests.post(url, json=payload, headers=headers,params=params, timeout=30)
        print(comapany_id,response.status_code)
        self.env["api.sent.invoice"].sudo().create({
            "move_id": move.id,
            "sent_date": fields.Datetime.now(),
            "response": response.text,
            "success": response.status_code in [200, 201],
        })

