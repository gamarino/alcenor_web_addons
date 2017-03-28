# -*- coding: utf-8 -*-
##############################################################################
#
#    NUMA
#    Copyright (C) 2017 NUMA Extreme Systems (<http:www.numaes.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import except_orm

from openerp.tools.translate import _

productFields = [
    'default_code',
    'active',
    'product_tmpl_id',
    'ean13',
    'attribute_value_ids',
    'image_variant',
]

class RemoteServer(models.Model):
    _inherit = 'dbsynch.remote_server'
    
    pos_group_name = fields.Char('Remote group name')
    
    @api.multi
    def get_master_type_selection(self):
        selection = super(RemoteServer, self).get_master_type_selection()
        selection.append(('pos_remote', _('POS Remote')))
        
        return sorted(selection, key=lambda o: o[1])

    @api.multi
    def getMasterObjects(self, bkJob):
        objectList = super(RemoteServer, self).getMasterObjects(bkJob)
        
        newObjects = []
        patchExistingSelector = False
        for remoteObject, selector in objectList:
            if remoteObject == 'pos.config':
                newSelector = []
                for source, op, value in selector:
                    if source == 'pos_group.name':
                        if op == '=':
                            value = self.pos_group_name
                            patchExistingSelector = True
                        elif op == 'in':
                            value.append(self.pos_group_name)
                            patchExistingSelector = True
                    newSelector.append((source, op, value))
                newObjects.append((remoteObject, newSelector))                
            else:
                newObjects.append((remoteObject, selector))                
        if not patchExistingSelector:
            newObjects.append(('pos.config', ('pos_group.name', '=', self.pos_group_name)))

        return newObjects

    @api.multi
    def getLocalObjects(self, bkJob):
        objectList = super(RemoteServer, self).getLocalObjects(bkJob)
        
        newObjects = []
        patchExistingSelector = False
        for localobject, selector in objectList:
            if localobject == 'pos.order':
                newSelector = []
                for source, op, value in selector:
                    if source == 'session_id.config_id.pos_group.name':
                        if op == '=':
                            value = self.pos_group_name
                            patchExistingSelector = True
                        elif op == 'in':
                            value.append(self.pos_group_name)
                            patchExistingSelector = True
                    newSelector.append((source, op, value))
                newObjects.append((localobject, newSelector))                
            else:
                newObjects.append((localobject, selector))                
        if not patchExistingSelector:
            newObjects.append(('pos.order', ('session_id.config_id.pos_group.name', '=', self.pos_group_name)))

        return newObjects

    @api.multi
    def processSpecialModels(self, modelName, defaultVals):

        def raiseWarning(identifier):
            raise except_orm(_('Error'),
                             _('On model %s, identifier %s was not found on local database! Please add the object and retry') % \
                              (modelName, identifier))

        if modelName == 'res.currency':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'res.country':
            ret = self.env[modelName].with_context(lang=self.lang).search([('code','=',defaultVals['code'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['code'])
        elif modelName == 'res.country.state':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name']),
                                                         ('country_id','=',defaultVals['country_id'])])
            if ret:
                return ret
            else:
                raiseWarning("Country_id: %d, name: %s" % (defaultVals['country_id'], defaultVals['name']))
        elif modelName == 'res.country.group':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'product.uom':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'product.uom.categ':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'product.ul':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'product.product':
            newVals = {}
            for fieldName in defaultVals.keys():
                if fieldName in productFields:
                    newVals[fieldName] = defaultVals[fieldName]

            return self.env['product.product'].create(newVals)
        elif modelName == 'decimal.precision':
            ret = self.env[modelName].with_context(lang=self.lang).search([('name','=',defaultVals['name'])])
            if ret:
                return ret
            else:
                raiseWarning(defaultVals['name'])
        elif modelName == 'pos.config':
            locationObj = self.env['stock.location']
            stock = locationObj.with_context(lang=self.lang).search([('company_id','=',defaultVals['company_id']),
                                        ('usage', '=', 'internal')])
            if not stock:
                vals = locationObj.default_get(locationObj.fields_get().keys())
                vals.update({
                        'name': 'Stock',
                        'usage': 'internal',
                        'company_id': defaultVals['company_id'],   
                    })
                newMainStock = locationObj.create(vals)
                defaultVals['stock_location_id'] = newMainStock.id

            journalObj = self.env['account.journal']
            journal = journalObj.search([('company_id','=',defaultVals['company_id']),
                                        ('journal_user', '=', True ), 
                                        ('type', 'in', ['bank', 'cash'])])
            if not journal:
                vals = journalObj.default_get(locationObj.fields_get().keys())
                vals.update({
                        'name': 'Sale',
                        'code': 'POS',
                        'journal_user': True,
                        'type': 'cash',
                        'company_id': defaultVals['company_id'],   
                    })
                newSaleJournal = journalObj.create(vals)
                defaultVals['journal_id'] = newSaleJournal.id

        return super(RemoteServer, self).processSpecialModels(modelName, defaultVals)
        
    
