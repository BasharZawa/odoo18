from odoo import models, fields
from odoo.exceptions import UserError


class SerialQualityReceiptWizard(models.TransientModel):
    _name = "quality.serial.receipt.wizard"
    _description = "Serial Quality Inspection for Vendor Receipt"

    picking_id = fields.Many2one(
        "stock.picking",
        required=True,
        readonly=True
    )

    scanned_serial = fields.Char(
        string="Scan Serial Number",
        required=True
    )

    inspected_count = fields.Integer(
        string="Inspected",
        compute="_compute_counters"
    )

    remaining_count = fields.Integer(
        string="Remaining",
        compute="_compute_counters"
    )

    # -------------------------------------------------
    # Counters
    # -------------------------------------------------

    def _compute_counters(self):
        for wiz in self:
            if not wiz.picking_id:
                wiz.inspected_count = 0
                wiz.remaining_count = 0
                continue

            # Total expected serials based on move quantities
            total_expected = sum(wiz.picking_id.move_ids.filtered(
                lambda m: m.product_id.tracking == 'serial'
            ).mapped('product_uom_qty'))

            inspected = self.env["quality.check"].search_count([
                ("picking_id", "=", wiz.picking_id.id),
                ("quality_state", "!=", "none"),
            ])

            wiz.inspected_count = inspected
            wiz.remaining_count = max(int(total_expected) - inspected, 0)

    # -------------------------------------------------
    # Main action (PASS)
    # -------------------------------------------------

    def action_scan_serial(self):
        self.ensure_one()

        serial = (self.scanned_serial or "").strip()
        if not serial:
            raise UserError("يرجى إدخال Serial Number")

        line = self._find_serial_line(serial)

        # prevent double inspection
        already = self.env["quality.check"].search_count([
            ("picking_id", "=", self.picking_id.id),
            ("note", "=", f"Serial: {serial}")
        ])
        if already:
            raise UserError("تم فحص هذا الـ Serial مسبقًا")

        # Try to find an existing 'none' check for this product
        check = self.env["quality.check"].search([
            ("picking_id", "=", self.picking_id.id),
            ("product_id", "=", line.product_id.id),
            ("quality_state", "=", "none")
        ], limit=1)

        vals = {
            "quality_state": "pass",
            "note": f"Serial: {serial}",
            "lot_id": line.lot_id.id if line.lot_id else False,
            "lot_name": line.lot_name if not line.lot_id else False,
            "user_id": self.env.user.id,
            "control_date": fields.Datetime.now(),
        }

        if check:
            check.write(vals)
        else:
            # create quality check if none exists (fallback)
            vals.update({
                "picking_id": self.picking_id.id,
                "product_id": line.product_id.id,
                "test_type": "passfail",
            })
            self.env["quality.check"].create(vals)

        self.scanned_serial = False
        return {"type": "ir.actions.client", "tag": "reload"}

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _find_serial_line(self, serial):
        """
        Find serial either in:
        - lot_name (before validate)
        - lot_id.name (after validate)
        If not found, try to create a new move line for a product that needs a serial.
        """
        # 1. Search in existing move lines
        line = self.picking_id.move_line_ids.filtered(
            lambda l: l.lot_name == serial or (l.lot_id and l.lot_id.name == serial)
        )
        if line:
            return line[0]

        # 2. If not found, find a move that still needs serials
        moves = self.picking_id.move_ids.filtered(
            lambda m: m.product_id.tracking == 'serial' and m.quantity < m.product_uom_qty
        )

        if not moves:
            raise UserError("هذا الـ Serial غير موجود، ولا يوجد كميات متبقية تتطلب Serial في هذا الاستلام")

        # Create a new move line for the first available move
        move = moves[0]
        new_line = self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': move.id,
            'product_id': move.product_id.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'lot_name': serial,
            'quantity': 1.0,
        })
        return new_line
