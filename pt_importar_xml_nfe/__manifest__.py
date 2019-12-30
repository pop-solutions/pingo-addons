# -*- coding: utf-8 -*-
{
    'name': "Importar XML da NFe",

    'summary': """
        Preencha automaticamente uma fatura de fornecedor baseado nos dados
        do XML da Nota Fiscal recebida.""",
    'description': """
        xml
        import
        brazil
        brasil
        importar xml
        importação de xml
        nota fiscal
        NFE
        NFSE
    """,
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
    'external_dependencies':{"python":[
        'xmltodict',
    ]},

    'data': [
        'views/account.invoice.xml',
        'wizard/importar_xml_nfe.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
