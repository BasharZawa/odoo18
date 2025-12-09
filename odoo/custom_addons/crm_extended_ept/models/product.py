
from odoo import models, fields, api


class ProductTemplateExtended(models.Model):
    _inherit = "product.template"

    model_number = fields.Char(string="Model Number", compute="_compute_model_number",
                               inverse="_set_model_number", store=True)
    product_line_id = fields.Many2one(comodel_name="product.line.ept", string="Product Line",
                                      compute="_compute_product_line",
                                      inverse="_set_product_line", store=True)
    product_nature_id = fields.Many2one(comodel_name="product.nature.ept", string="Product Nature",
                                        compute="_compute_product_nature",
                                        inverse="_set_product_nature", store=True)

    @api.depends('product_variant_ids.model_number')
    def _compute_model_number(self):
        self._compute_template_field_from_variant_field('model_number')

    def _set_model_number(self):
        self._set_product_variant_field('model_number')

    @api.depends('product_variant_ids.product_line_id')
    def _compute_product_line(self):
        self._compute_template_field_from_variant_field('product_line_id')

    def _set_product_line(self):
        self._set_product_variant_field('product_line_id')

    @api.depends('product_variant_ids.product_line_id')
    def _compute_product_nature(self):
        self._compute_template_field_from_variant_field('product_nature_id')

    def _set_product_nature(self):
        self._set_product_variant_field('product_nature_id')

class ProductProductExtended(models.Model):
    _inherit = "product.product"

    model_number = fields.Char(string="Model Number")
    product_line_id = fields.Many2one(comodel_name="product.line.ept", string="Product Line")
    product_nature_id = fields.Many2one(comodel_name="product.nature.ept", string="Product Nature")
