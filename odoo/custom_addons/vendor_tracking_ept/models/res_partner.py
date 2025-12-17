# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_type = fields.Selection(
        selection=[
            ('customer', 'Customer'),
            ('vendor', 'Vendor'),
            ('both', 'Both'),
        ],
        string='Contact Type',
        help='Defines whether this contact is a customer, a vendor, or both.',
        tracking=True,
        copy=False,
        index=True,
    )

    vendor_code = fields.Char(
        string='Vendor Code',
        copy=False,
        index=True,
        help='System-generated code for vendor identification. Immutable once assigned.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResPartner, self).create(vals_list)
        for record, vals in zip(records, vals_list):
            # Auto-generate only if designated as vendor or both and vendor_code is empty
            contact_type_value = vals.get('contact_type') or record.contact_type
            if contact_type_value in ('vendor', 'both') and not record.vendor_code:
                record._assign_vendor_code()
        return records

    def write(self, vals):
        # Prevent manual change to vendor_code after assignment
        if 'vendor_code' in vals:
            for partner in self:
                if partner.vendor_code and vals['vendor_code'] != partner.vendor_code:
                    raise UserError(_('Vendor Code is immutable once assigned.'))
        res = super(ResPartner, self).write(vals)
        # Assign code for records that just turned into vendor/both and lack a code
        if 'contact_type' in vals:
            for partner in self:
                if partner.contact_type in ('vendor', 'both') and not partner.vendor_code:
                    partner._assign_vendor_code()
        return res

    def _assign_vendor_code(self):
        self.ensure_one()
        if self.vendor_code:
            return
        if not self.country_id:
            raise UserError("Country is not set.")
        country_code = self.country_id.code or "XX"
        prefix = self.country_id.sequence_prefix or ""
        if not len(prefix):
            if self.country_id.name:
                prefix = self.country_id.name[:3].upper()
                self.country_id.sequence_prefix = prefix
        sequence = self.env["ir.sequence"].sudo().search([
            ("code", "=", f"vendor.{country_code}")
        ], limit=1)

        if sequence:
            sequence.write({"prefix": f"{prefix}"})
        else:
            sequence = self.env["ir.sequence"].sudo().create({
                "name": f"Vendor Sequence {country_code}",
                "code": f"vendor.{country_code}",
                "prefix": f"{prefix}",
                "padding": 5,
                "company_id": False
            })
        code = sequence.next_by_code(f"vendor.{country_code}")
        self.vendor_code = code
        if self.ref:
            self.ref = f"{self.ref} | {code}"
        else:
            self.ref = code
