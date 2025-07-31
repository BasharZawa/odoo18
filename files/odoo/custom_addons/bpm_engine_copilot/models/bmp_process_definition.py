# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


class BmpProcessDefinition(models.Model):
    _name = 'bmp.process.definition'
    _description = 'BPMN Process Definition'
    _order = 'name, version desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Process Name',
        required=True,
        index=True,
        help='Name of the BPMN process'
    )
    
    version = fields.Char(
        string='Version',
        required=True,
        default='1.0',
        help='Version of the process definition'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Full display name with version'
    )
    
    xml_data = fields.Text(
        string='BPMN XML',
        required=True,
        help='BPMN 2.0 XML definition of the process'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the process'
    )
    
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Only active process definitions can be instantiated'
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True
    )
    
    updated_at = fields.Datetime(
        string='Updated At',
        default=fields.Datetime.now,
        readonly=True
    )
    
    # Computed fields for statistics
    instance_count = fields.Integer(
        string='Total Instances',
        compute='_compute_instance_statistics'
    )
    
    active_instance_count = fields.Integer(
        string='Active Instances',
        compute='_compute_instance_statistics'
    )
    
    completed_instance_count = fields.Integer(
        string='Completed Instances',
        compute='_compute_instance_statistics'
    )
    
    # One2many relationships
    process_instances = fields.One2many(
        'bmp.process.instance',
        'process_definition_id',
        string='Process Instances'
    )
    
    # Technical fields
    parsed_xml_data = fields.Text(
        string='Parsed XML Data',
        help='Internal parsed XML data for performance'
    )
    
    start_events = fields.Text(
        string='Start Events',
        help='JSON list of start events in the process'
    )
    
    @api.depends('name', 'version')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} v{record.version}"
    
    @api.depends('process_instances.state')
    def _compute_instance_statistics(self):
        for record in self:
            instances = record.process_instances
            record.instance_count = len(instances)
            record.active_instance_count = len(instances.filtered(
                lambda i: i.state in ['draft', 'running']
            ))
            record.completed_instance_count = len(instances.filtered(
                lambda i: i.state == 'completed'
            ))
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['updated_at'] = fields.Datetime.now()
        records = super().create(vals_list)
        for record in records:
            record._validate_and_parse_xml()
        return records
    
    def write(self, vals):
        if 'xml_data' in vals:
            vals['updated_at'] = fields.Datetime.now()
        result = super().write(vals)
        if 'xml_data' in vals:
            for record in self:
                record._validate_and_parse_xml()
        return result
    
    def _validate_and_parse_xml(self):
        """Validate BPMN XML and extract key information"""
        try:
            if not self.xml_data:
                raise ValidationError(_("BPMN XML data is required"))
            
            # Parse XML
            root = ET.fromstring(self.xml_data)
            
            # Basic BPMN validation
            if root.tag.split('}')[-1] != 'definitions':
                raise ValidationError(_("Invalid BPMN XML: Root element must be 'definitions'"))
            
            # Extract start events
            start_events = []
            for elem in root.iter():
                if elem.tag.split('}')[-1] == 'startEvent':
                    start_events.append({
                        'id': elem.get('id'),
                        'name': elem.get('name', ''),
                    })
            
            self.start_events = json.dumps(start_events)
            self.parsed_xml_data = self.xml_data
            
        except ET.ParseError as e:
            raise ValidationError(_("Invalid XML format: %s") % str(e))
        except Exception as e:
            _logger.error("Error parsing BPMN XML: %s", str(e))
            raise ValidationError(_("Error parsing BPMN XML: %s") % str(e))
    
    def action_activate(self):
        """Activate this process definition and deactivate others with same name"""
        other_versions = self.search([
            ('name', '=', self.name),
            ('id', '!=', self.id)
        ])
        other_versions.write({'is_active': False})
        self.write({'is_active': True})
        return True
    
    def action_create_instance(self):
        """Create a new process instance from this definition"""
        if not self.is_active:
            raise UserError(_("Cannot create instance from inactive process definition"))
        
        instance = self.env['bmp.process.instance'].create({
            'process_definition_id': self.id,
            'state': 'draft',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Instance'),
            'res_model': 'bmp.process.instance',
            'res_id': instance.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_instances(self):
        """View all instances of this process definition"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Instances'),
            'res_model': 'bmp.process.instance',
            'view_mode': 'tree,form',
            'domain': [('process_definition_id', '=', self.id)],
            'context': {'default_process_definition_id': self.id},
        }
    
    @api.constrains('name', 'version')
    def _check_unique_name_version(self):
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('version', '=', record.version),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_(
                    "A process definition with name '%s' and version '%s' already exists"
                ) % (record.name, record.version))