# -*- coding: utf-8 -*-
{
    'name': "Importar XML da NFe",
    'license': 'AGPL-3',
    'summary': """
        Preencha automaticamente uma fatura de fornecedor baseado nos dados
        do XML da Nota Fiscal recebida.""",

    'description': """
    """,
    'price': 99.0,
    'currency': 'EUR',
    'author': "Pingo Tecnologia",
    'support': 'contato@pingotecnologia.com.br',
    'images': ['static/description/capa.jpg'],
    'website': "http://www.pingotecnologia.com",

    'category': 'Accounting & Finance',
    'version': '11.0.1',

    'depends': ['base',
    'br_base',
    'br_account',
    'br_account_einvoice',
    'document',
    'account',
    'stock',
    'delivery'
    ],

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
