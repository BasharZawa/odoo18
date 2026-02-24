# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    def _set_scheduled_date(self):
        """Set move line dates to match the scheduled date of picking"""
        for picking in self:
            picking.move_line_ids.write({'date': picking.scheduled_date})

class BackDateWiz(models.TransientModel):
    _name = 'backdate.entries.wiz'
    _description = "Backdate Wizard"

    date = fields.Datetime('Date', default=fields.Datetime.now)
    picking_ids = fields.Many2many('stock.picking')

    def change_to_backdate_wizard(self):
        """Opens the backdate wizard form view"""
        return {
            'name': 'Backdate Transfer',
            'res_model': 'backdate.entries.wiz',
            'view_mode': 'form',
            'view_id': self.env.ref('cr_backdate_entries.backdate_wizard_view_form').id,
            'target': 'new',
            'type': 'ir.actions.act_window'
        }

    def change_to_backdate(self):
        """Apply backdate changes to sale orders, purchase orders, or stock pickings"""
        active_model = self._context.get('active_model')

        if active_model == 'sale.order':
            self._update_sale_orders()
        elif active_model == 'purchase.order':
            self._update_purchase_orders()
        elif active_model == 'stock.quant':
            self._update_stock_quant()
        elif active_model == 'stock.picking':
            self._update_stock_picking()
        elif active_model == 'stock.scrap':
            self._update_stock_scrap()
        elif active_model == 'mrp.production':
            self._update_mrp_order()

    def _update_mrp_order(self):
        """Update Dates for Manufacturing Order"""
        mrp_production_ids = self.env['mrp.production'].browse(self._context.get('active_ids'))
        for mrp in mrp_production_ids:
            self.env.cr.execute('UPDATE mrp_production SET date_start=%s WHERE id=%s',
                                (self.date, mrp.id))
            self._update_stock_moves(mrp.all_move_ids)

    def _update_stock_scrap(self):
        """Update Dates for Scrap Stock and related records"""
        scrap_stock_ids = self.env['stock.scrap'].browse(self._context.get('active_ids'))
        for stock in scrap_stock_ids:
            stock.date_done = self.date
            self._update_stock_moves(stock.move_ids)

    def _update_sale_orders(self):
        """Update dates for sale orders and related records"""
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids'))
        for sale in sale_orders:
            sale.date_order = self.date
            self._update_pickings(sale.picking_ids)
            self._update_invoices(sale.invoice_ids)

    def _update_purchase_orders(self):
        """Update dates for purchase orders and related records"""
        purchase_orders = self.env['purchase.order'].browse(self._context.get('active_ids'))
        for purchase in purchase_orders:
            purchase.date_approve = self.date
            purchase.date_order = self.date
            self._update_pickings(purchase.picking_ids)
            self._update_invoices(purchase.invoice_ids)

    def _update_stock_quant(self):
        """Update inventory date and related stock move records"""
        stock_quants = self.env['stock.quant'].browse(self._context.get('active_ids'))
        for quant in stock_quants:
            quant.inventory_date = self.date
            move_lines = self.env['stock.move.line'].search([('quant_id', '=', quant.id)])
            self._update_stock_moves(move_lines.mapped('move_id'))

    def _update_stock_picking(self):
        """Update dates for stock pickings"""
        pickings = self.env['stock.picking'].browse(self._context.get('active_ids'))
        self._update_pickings(pickings)

    def _update_pickings(self, pickings):
        """Update stock picking and related stock moves"""
        for picking in pickings:
            moves = picking.move_ids
            self._update_stock_moves(moves)

            picking.write({
                'scheduled_date': self.date,
                'date_deadline': self.date,
                'date_done': self.date,
            })

    def _update_stock_moves(self, moves):
        """Update stock moves and related valuation layers"""
        for move in moves:
            move.write({'date': self.date})

            # Update stock valuation layers
            valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
            for layer in valuation_layers:
                self.env.cr.execute('UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s',
                                    (self.date, layer.id))

            # Update stock move lines
            move.move_line_ids.write({'date': self.date})

    def _update_invoices(self, invoices):
        """Update account moves (invoices)"""
        for invoice in invoices:
            if invoice.state == 'draft':
                invoice.write({'date': self.date, 'invoice_date': self.date})
            elif invoice.state == 'posted':
                invoice.button_draft()
                invoice.write({'name': False, 'date': self.date, 'invoice_date': self.date})
                invoice.action_post()

            invoice.invoice_line_ids.write({'date': self.date})
            invoice.line_ids.write({'date': self.date})
