# -*- coding: utf-8 -*-
{
    'name': "Importar XML da NFe",

    'summary': """
        Preencha automaticamente uma fatura de fornecedor baseado nos dados
        do XML da Nota Fiscal recebida.""",

    'description': """
    """,
    'price': 59.0,
    'currency': 'EUR',
    'author': "Pingo Tecnologia",
    'support': 'contato@pingotecnologia.com.br',
    'images': ['static/description/capa.jpg'],
    'website': "http://www.pingotecnologia.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting & Finance',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
    'br_base',
    'br_account',
    'br_account_einvoice',
    'document',
    'account',
    'stock',
    'delivery'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/account.invoice.xml',
        'views/account_invoice_line.xml',
        'wizard/importar_xml_nfe.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
