from odoo import models, fields, api

class Appointment(models.Model):
    _name = 'appointment'
    _description = 'Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Appointment Name', required=True)
    date = fields.Datetime(string='Date', required=True)
    patient_id = fields.Many2one('patient', string='Patient', required=True)
    status = fields.Selection([
        ('new', 'New'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('canceled', 'Canceled'),
        ('completed', 'Completed'),
    ], string='Status', default='new')
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')

    def print_appointment(self):
        # This method can be used to print the appointment details
        print("Printing appointment details...")
        for appointment in self:
            print(f"Appointment ID: {appointment.id}")
            print(f"Patient: {appointment.patient_id.name}")
            print(f"Date: {appointment.date}")
            print(f"Status: {appointment.status}")
            print(f"Description: {appointment.description}")
            print(f"Notes: {appointment.notes}")


