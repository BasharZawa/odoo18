# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_id = fields.Char(
        string='Customer ID',
        copy=False,
        help="Unique identifier for customer contacts"
    )

    validation_status = fields.Selection(
        [('not_validated', 'Not Validated'), ('validated', 'Validated')],
        string='Validation Status',
        default='not_validated',
        required=True,
        copy=False,
        help="Indicates if the customer contact has been validated"
    )

    validation_date = fields.Datetime(
        string='Validation Date',
        help="Date when the customer contact was validated"
    )

    validated_by = fields.Many2one(
        'res.users',
        string='Validated By',
        help="User who validated this customer contact"
    )

    validation_notes = fields.Text(
        string='Validation Notes',
        help="Notes from the Finance team regarding validation"
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResPartner, self).create(vals_list)
        for record, vals in zip(records, vals_list):
            contact_type_value = vals.get('contact_type') or record.contact_type
            if contact_type_value in ('customer', 'both') and not record.customer_id:
                record._generate_customer_id()
        return records

    def _generate_customer_id(self):
        """Generate unique Customer ID using sequence"""
        self.ensure_one()
        if not self.customer_id and self.contact_type in ('customer', 'both'):
            if not self.country_id:
                raise UserError("Partner Country is not set.")
            country_code = self.country_id.code or "XX"
            prefix = self.country_id.sequence_prefix or ""
            if not len(prefix):
                if self.country_id.name:
                    prefix = self.country_id.name[:3].upper()
                    self.country_id.sequence_prefix = prefix
            sequence = self.env["ir.sequence"].sudo().search([
                ("code", "=", f"customer.{country_code}")
            ], limit=1)

            if sequence:
                sequence.write({"prefix": f"{prefix}"})
            else:
                sequence = self.env["ir.sequence"].sudo().create({
                    "name": f"Customer Sequence {country_code}",
                    "code": f"customer.{country_code}",
                    "prefix": f"{prefix}",
                    "padding": 5,
                    "company_id": False
                })
            code = sequence.next_by_code(f"customer.{country_code}")
            self.customer_id = code
            # if self.ref:
            #     self.ref = f"{self.ref} | {code}"
            # else:
            #     self.ref = code

    def action_validate_customer(self):
        """Validate customer contact - Finance team only"""
        self.ensure_one()

        if not self.env.user.has_group('customer_management_ept.group_finance_team'):
            raise UserError(_('Only Finance team members can validate customer contacts.'))

        if self.validation_status == 'validated':
            raise UserError(_('This customer contact is already validated.'))

        self.write({
            'validation_status': 'validated',
            'validation_date': fields.Datetime.now(),
            'validated_by': self.env.user.id,
        })
        if not self.contact_type:
            self.contact_type = 'customer'
        if self.contact_type in ("customer", "both") and not self.customer_id:
            self._generate_customer_id()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Customer Validated'),
                'message': _(
                    'Customer %s has been successfully validated. Refresh the current record for updated values.') % self.name,
                'type': 'success',
            }
        }

    def action_invalidate_customer(self):
        """Invalidate customer contact - Finance Manager only"""
        self.ensure_one()

        if not self.env.user.has_group('customer_management_ept.group_finance_team'):
            raise UserError(_('Only Finance Team can invalidate customer contacts.'))

        if self.validation_status != 'validated':
            raise UserError(_('This customer contact is not validated.'))

        confirmed_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.id),
            ('state', 'in', ['sale', 'done'])
        ])
        if confirmed_orders:
            raise UserError(_('Cannot invalidate customer with confirmed sales orders.'))

        self.write({
            'validation_status': 'not_validated',
            'validation_date': False,
            'validated_by': False,
            'validation_notes': False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Customer Invalidated'),
                'message': _(
                    'Customer %s has been invalidated. Refresh the current record for updated values.') % self.name,
                'type': 'warning',
            }
        }

    @api.constrains('validation_status', 'contact_type')
    def _check_customer_validation(self):
        """Ensure constraints when validated"""
        for partner in self:
            if partner.contact_type in ('customer', 'both') and partner.validation_status == 'validated':
                if not partner.validation_date or not partner.validated_by:
                    raise ValidationError(_('Validated customers must have validation date and validator.'))

    def write(self, vals):
        """Override write to enforce field-level access rules based on validation status and user group"""
        for partner in self:
            # Prevent modification of immutable Customer ID
            if "customer_id" in vals and partner.customer_id and vals["customer_id"] != partner.customer_id:
                raise UserError(_("Customer ID is immutable once assigned."))

            user = self.env.user
            is_finance = user.has_group("customer_management_ept.group_finance_team")

            if not self.env.context.get("check_bypass") and (partner.contact_type in ("customer", "both") or (
                    "contact_type" in vals and vals.get("contact_type") in ("customer", "both"))):
                if partner.validation_status == "validated":
                    if not is_finance:
                        # Sales Team → only phone, mobile, email can be updated
                        editable_fields = {"phone", "mobile", "email"}
                        restricted_fields = set(vals.keys()) - editable_fields
                        if restricted_fields:
                            raise UserError(
                                _("You cannot modify %s for validated customers. "
                                  "Only Finance team can edit validated customer data.")
                                % ", ".join(restricted_fields)
                            )
                elif partner.validation_status == "not_validated":
                    if not is_finance:
                        # Sales Team → full rights on unvalidated customers
                        pass
                    else:
                        # Finance Team → read-only, except notes
                        editable_fields = {"comment"}
                        restricted_fields = set(vals.keys()) - editable_fields
                        if restricted_fields:
                            raise UserError(
                                _("Finance team cannot modify %s until the customer is validated.")
                                % ", ".join(restricted_fields)
                            )

        # ✅ No recursion here
        res = super().write(vals)

        if "contact_type" in vals:
            for partner in self:
                if partner.contact_type in ("customer", "both") and not partner.customer_id:
                    partner._generate_customer_id()
        return res

    def unlink(self):
        for partner in self:
            if partner.validation_status == 'validated' and not self.env.user.has_group(
                    'customer_management_ept.group_finance_team'):
                raise UserError(
                    _('Cannot delete validated customers. Only Finance Team can delete validated customers.'))
        return super(ResPartner, self).unlink()
