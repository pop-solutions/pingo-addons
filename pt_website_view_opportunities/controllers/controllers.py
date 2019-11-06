# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http, _
import base64
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager


class CustomerPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
      values = super(CustomerPortal, self)._prepare_portal_layout_values()
      partner = request.env.uid

      Oporttunities = request.env['crm.lead']
      opportunities_count = Oporttunities.search_count([
          ('user_id','=',partner)
      ])

      values.update({
          'opportunities_count': opportunities_count,
      })
      return values

    @http.route(['/my/opportunities', '/my/opportunities/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_opportunities(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.uid
        Opportunity = request.env['crm.lead']

        domain = [('user_id','=',partner)]

        searchbar_sortings = {
            'date': {'label': _('Open Date'), 'order': 'date_open desc'},
            'name': {'label': _('Opportunity'), 'order': 'name'},
            'name': {'label': _('Stage'), 'order': 'stage_id.name'},
        }

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('crm.lead', domain)
        if date_begin and date_end:
            domain += [('date_open', '>', date_begin), ('date_open', '<=', date_end)]

        # count for pager
        opportunity_count = Opportunity.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/opportunities",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=opportunity_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        opportunities = Opportunity.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        #request.session['my_opportunities_history'] = opportunities.ids[:100]

        values.update({
            'date': date_begin,
            'opportunities': opportunities.sudo(),
            'page_name': 'opportunity',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/opportunities',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("pt_website_view_opportunities.portal_my_opportunities", values)

    def _opportunity_get_page_view_values(self, opportunity, access_token, **kwargs):
        values = {
            'page_name': 'opportunity',
            'opportunity': opportunity,
        }
        return self._get_page_view_values(opportunity, access_token, values, 'my_opportunity_history', False, **kwargs)


    @http.route(['/my/opportunities/<int:opportunity_id>'], type='http', auth="user", website=True)
    def portal_my_opportunity(self, opportunity_id=None, access_token=None, **kw):
        try:
            opportunity_sudo = self._document_check_access('crm.lead', opportunity_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._opportunity_get_page_view_values(opportunity_sudo, access_token, **kw)
        attachments = request.env['ir.attachment'].search([('res_id','=',opportunity_id)])
        values.update({'attachments':attachments})
        return request.render("pt_website_view_opportunities.portal_my_opportunity", values)

    @http.route('/opportunity/uploaded', type='http', auth="user", website=True)
    def upload_files(self, **post):
        values = {}
        if post.get('attachment',False):
            Attachments = request.env['ir.attachment']
            name = post.get('attachment').filename
            file = post.get('attachment')
            opportunity_id = post.get('opportunity_id')
            attachment = file.read()
            attachment_id = Attachments.sudo().create({
                'name':name,
                'datas_fname': name,
                'res_name': name,
                'type': 'binary',
                'res_model': 'crm.lead',
                'res_id': opportunity_id,
                'datas': base64.b64encode(attachment),
            })
            value = {
                'attachment' : attachment_id
            }
        return http.local_redirect("/my/opportunities", value)
