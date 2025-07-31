# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta
from odoo import fields

_logger = logging.getLogger(__name__)


class BmpTokenManager:
    """Token Manager for BPMN Process Execution"""
    
    def __init__(self, env):
        self.env = env
    
    def create_token(self, process_instance, element_id, element_data=None):
        """Create a new token at the specified element"""
        token_id = f"token_{element_id}_{datetime.now().timestamp()}"
        
        token_data = {
            'id': token_id,
            'element_id': element_id,
            'element_data': element_data or {},
            'created_at': fields.Datetime.now().isoformat(),
            'status': 'active',
            'variables': {},
        }
        
        # Store token in process instance data
        self._add_token_to_process(process_instance, token_data)
        
        _logger.info("Created token %s at element %s for process %s", token_id, element_id, process_instance.id)
        
        return token_data
    
    def get_active_tokens(self, process_instance):
        """Get all active tokens for a process instance"""
        process_data = self._get_process_data(process_instance)
        tokens = process_data.get('tokens', [])
        return [token for token in tokens if token.get('status') == 'active']
    
    def get_token_by_id(self, process_instance, token_id):
        """Get a specific token by ID"""
        process_data = self._get_process_data(process_instance)
        tokens = process_data.get('tokens', [])
        
        for token in tokens:
            if token.get('id') == token_id:
                return token
        
        return None
    
    def get_tokens_at_element(self, process_instance, element_id):
        """Get all active tokens at a specific element"""
        active_tokens = self.get_active_tokens(process_instance)
        return [token for token in active_tokens if token.get('element_id') == element_id]
    
    def move_token(self, process_instance, token_id, new_element_id):
        """Move a token to a new element"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            _logger.error("Token %s not found for process %s", token_id, process_instance.id)
            return False
        
        old_element_id = token.get('element_id')
        token['element_id'] = new_element_id
        token['moved_at'] = fields.Datetime.now().isoformat()
        
        self._update_token_in_process(process_instance, token)
        
        _logger.info("Moved token %s from %s to %s in process %s", 
                    token_id, old_element_id, new_element_id, process_instance.id)
        
        return True
    
    def consume_token(self, process_instance, token_id):
        """Remove/consume a token from the process"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            _logger.error("Token %s not found for process %s", token_id, process_instance.id)
            return False
        
        token['status'] = 'consumed'
        token['consumed_at'] = fields.Datetime.now().isoformat()
        
        self._update_token_in_process(process_instance, token)
        
        _logger.info("Consumed token %s at element %s in process %s", 
                    token_id, token.get('element_id'), process_instance.id)
        
        return True
    
    def split_token(self, process_instance, source_token_id, target_element_ids):
        """Split a token into multiple tokens for parallel execution"""
        source_token = self.get_token_by_id(process_instance, source_token_id)
        if not source_token:
            _logger.error("Source token %s not found for process %s", source_token_id, process_instance.id)
            return []
        
        # Consume the source token
        self.consume_token(process_instance, source_token_id)
        
        # Create new tokens for each target element
        new_tokens = []
        for element_id in target_element_ids:
            # Inherit variables from source token
            new_token = self.create_token(process_instance, element_id, source_token.get('element_data'))
            new_token['variables'] = source_token.get('variables', {}).copy()
            new_token['parent_token_id'] = source_token_id
            
            self._update_token_in_process(process_instance, new_token)
            new_tokens.append(new_token)
        
        _logger.info("Split token %s into %d tokens for elements %s in process %s", 
                    source_token_id, len(new_tokens), target_element_ids, process_instance.id)
        
        return new_tokens
    
    def merge_tokens(self, process_instance, token_ids, target_element_id):
        """Merge multiple tokens into a single token"""
        if not token_ids:
            return None
        
        tokens = []
        for token_id in token_ids:
            token = self.get_token_by_id(process_instance, token_id)
            if token:
                tokens.append(token)
        
        if not tokens:
            _logger.error("No valid tokens found for merge in process %s", process_instance.id)
            return None
        
        # Consume all source tokens
        for token in tokens:
            self.consume_token(process_instance, token['id'])
        
        # Create merged token
        merged_token = self.create_token(process_instance, target_element_id)
        
        # Merge variables from all tokens
        merged_variables = {}
        for token in tokens:
            token_vars = token.get('variables', {})
            merged_variables.update(token_vars)
        
        merged_token['variables'] = merged_variables
        merged_token['source_token_ids'] = token_ids
        
        self._update_token_in_process(process_instance, merged_token)
        
        _logger.info("Merged %d tokens into token %s at element %s in process %s", 
                    len(tokens), merged_token['id'], target_element_id, process_instance.id)
        
        return merged_token
    
    def set_token_variable(self, process_instance, token_id, key, value):
        """Set a variable on a specific token"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            _logger.error("Token %s not found for process %s", token_id, process_instance.id)
            return False
        
        if 'variables' not in token:
            token['variables'] = {}
        
        token['variables'][key] = value
        self._update_token_in_process(process_instance, token)
        
        return True
    
    def get_token_variable(self, process_instance, token_id, key, default=None):
        """Get a variable from a specific token"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            return default
        
        return token.get('variables', {}).get(key, default)
    
    def pause_token(self, process_instance, token_id):
        """Pause a token (for waiting states)"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            return False
        
        token['status'] = 'paused'
        token['paused_at'] = fields.Datetime.now().isoformat()
        
        self._update_token_in_process(process_instance, token)
        return True
    
    def resume_token(self, process_instance, token_id):
        """Resume a paused token"""
        token = self.get_token_by_id(process_instance, token_id)
        if not token:
            return False
        
        token['status'] = 'active'
        token['resumed_at'] = fields.Datetime.now().isoformat()
        
        self._update_token_in_process(process_instance, token)
        return True
    
    def get_token_history(self, process_instance, include_consumed=False):
        """Get the history of all tokens in the process"""
        process_data = self._get_process_data(process_instance)
        tokens = process_data.get('tokens', [])
        
        if not include_consumed:
            tokens = [token for token in tokens if token.get('status') != 'consumed']
        
        # Sort by creation time
        return sorted(tokens, key=lambda t: t.get('created_at', ''))
    
    def clean_consumed_tokens(self, process_instance, older_than_hours=24):
        """Clean up old consumed tokens to prevent data bloat"""
        process_data = self._get_process_data(process_instance)
        tokens = process_data.get('tokens', [])
        
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        cutoff_iso = cutoff_time.isoformat()
        
        cleaned_tokens = []
        removed_count = 0
        
        for token in tokens:
            if (token.get('status') == 'consumed' and 
                token.get('consumed_at', '') < cutoff_iso):
                removed_count += 1
            else:
                cleaned_tokens.append(token)
        
        if removed_count > 0:
            process_data['tokens'] = cleaned_tokens
            process_instance.process_data = json.dumps(process_data)
            _logger.info("Cleaned %d old consumed tokens from process %s", 
                        removed_count, process_instance.id)
        
        return removed_count
    
    def _get_process_data(self, process_instance):
        """Get the process data dictionary"""
        try:
            return json.loads(process_instance.process_data or '{}')
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def _add_token_to_process(self, process_instance, token_data):
        """Add a token to the process instance data"""
        process_data = self._get_process_data(process_instance)
        
        if 'tokens' not in process_data:
            process_data['tokens'] = []
        
        process_data['tokens'].append(token_data)
        process_instance.process_data = json.dumps(process_data)
    
    def _update_token_in_process(self, process_instance, updated_token):
        """Update a token in the process instance data"""
        process_data = self._get_process_data(process_instance)
        tokens = process_data.get('tokens', [])
        
        for i, token in enumerate(tokens):
            if token.get('id') == updated_token.get('id'):
                tokens[i] = updated_token
                break
        
        process_data['tokens'] = tokens
        process_instance.process_data = json.dumps(process_data)
    
    def get_statistics(self, process_instance):
        """Get token statistics for the process"""
        tokens = self.get_token_history(process_instance, include_consumed=True)
        
        stats = {
            'total_tokens': len(tokens),
            'active_tokens': len([t for t in tokens if t.get('status') == 'active']),
            'paused_tokens': len([t for t in tokens if t.get('status') == 'paused']),
            'consumed_tokens': len([t for t in tokens if t.get('status') == 'consumed']),
        }
        
        # Element distribution
        element_counts = {}
        for token in tokens:
            element_id = token.get('element_id')
            if element_id:
                element_counts[element_id] = element_counts.get(element_id, 0) + 1
        
        stats['element_distribution'] = element_counts
        
        return stats