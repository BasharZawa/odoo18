# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

JWT_TTL_SECONDS = 600


class MetabaseEmbedController(http.Controller):
    """Renders a Metabase dashboard inside Odoo for authenticated users.

    Security pattern:
      * Use sudo() only to READ config and dashboard metadata — the viewer
        group has no ACL on ir.config_parameter or metabase.dashboard by
        default, and an AccessError would leak a 500 before we emit 403.
      * Authorize against request.env.user.groups_id (the REAL user),
        never against a sudoed recordset — sudo bypasses record rules.
    """

    @http.route(
        '/metabase/embed/<string:code>',
        type='http', auth='user', website=False, csrf=False,
    )
    def embed(self, code, **_kwargs):
        dashboard = request.env['metabase.dashboard'].sudo().search(
            [('code', '=', code), ('active', '=', True)],
            limit=1,
        )
        if not dashboard:
            return request.not_found()

        user = request.env.user
        if not (user.groups_id & dashboard.allowed_group_ids):
            return request.make_response('Forbidden', status=403)

        ICP = request.env['ir.config_parameter'].sudo()
        site_url = (ICP.get_param('sedco_metabase_reports.site_url') or '').strip()
        secret = (ICP.get_param('sedco_metabase_reports.jwt_secret') or '').strip()
        if not site_url or not secret or dashboard.metabase_id <= 0:
            _logger.warning(
                "Metabase embed misconfigured for code=%s "
                "(site_url set=%s, secret set=%s, metabase_id=%s)",
                code, bool(site_url), bool(secret), dashboard.metabase_id,
            )
            return request.make_response('Embed not configured', status=403)

        locked_params = self._compute_locked_params(dashboard, user)
        token = self._sign_jwt(dashboard.metabase_id, locked_params, secret)
        iframe_src = (
            f"{site_url.rstrip('/')}/embed/dashboard/{token}"
            "#bordered=true&titled=true"
        )

        return request.render(
            'sedco_metabase_reports.embed_page',
            {
                'dashboard': dashboard,
                'iframe_src': iframe_src,
            },
        )

    @staticmethod
    def _compute_locked_params(dashboard, user):
        mode = dashboard.filter_mode
        if mode == 'none':
            return {}
        if mode == 'salesperson':
            return {'salesperson_id': user.id}
        if mode == 'salesperson_bypass_manager':
            if dashboard.bypass_group_id and dashboard.bypass_group_id in user.groups_id:
                return {'salesperson_id': []}
            return {'salesperson_id': user.id}
        return {}

    @staticmethod
    def _sign_jwt(metabase_id, locked_params, secret):
        def _b64url(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

        header = _b64url(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
        payload_data = {
            'resource': {'dashboard': metabase_id},
            'params': locked_params,
            'exp': int(time.time()) + JWT_TTL_SECONDS,
        }
        body = _b64url(json.dumps(payload_data, separators=(',', ':')).encode())
        msg = f"{header}.{body}".encode()
        sig = _b64url(hmac.new(secret.encode(), msg, hashlib.sha256).digest())
        return f"{header}.{body}.{sig}"
