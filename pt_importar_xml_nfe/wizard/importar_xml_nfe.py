# -*- coding: utf-8 -*-

import base64
import re
from io import BytesIO
from odoo import api, fields, models, exceptions
from nfelib.v4_00 import leiauteNFe_sub as parser

class ImportarXML(models.TransientModel):
    _name = 'importar.xml.nfe'
    _description = "Assistente de Importação do Arquivo XML"

    invoice_id = fields.Many2one(
        'account.invoice',
        string="Fatura do Fornecedor")

    xml = fields.Binary(
        string='Arquivo XML',
        help="Insira o arquivo XML enviado pelo seu fornecedor")

    importar_empresa_dif = fields.Boolean(
        string="Forçar importação de empresa diferente da minha",
        help="Importa o XML mesmo se a empresa destinatária da NFe não for a sua"
    )

    account_id = fields.Many2one(
        'account.account',
        string="Conta")

    account_analytic_id = fields.Many2one(
        'account.analytic.account',
        string="Conta Analítica",
        help="""Caso seja selecionada esta conta será utilizada em todas as linhas da fatura""")

    criar_fornecedor = fields.Boolean(
        string="Criar Fornecedor Automaticamente",
        help="""Irá criar automaticamente um fornecedor com base nos dados da fatura""")

    criar_transportadora = fields.Boolean(
        string="Criar Transportadora Automaticamente",
        help="""Irá criar automaticamente um fornecedor com base nos dados da fatura""")
    fornecedor_como_cliente = fields.Boolean(
        string="Marcar Fornecedor como Cliente",
        help="""Irá marcar o fornecedor criado como um cliente no sistema para ser utilizado no módulo de vendas""")

    criar_produtos = fields.Boolean(
        string="Criar Produtos Automaticamente",
        help="""Irá criar automaticamente produtos com base nos dados da Nota Fiscal.""")

    atualizar_produtos = fields.Boolean(
        string="Atualizar produtos existentes",
        help="""Irá substituir os dados dos  produtos cadastrados no fornecedor, caso existam.""")

    posicao_fiscal = fields.Many2one(
        "account.fiscal.position",
        string="Posição Fiscal",
        help="Selecione a Posição Fiscal que será utilizada nesta fatura.")

    ##############################################################################
    #Função de Importação da NFe

    def importar_xml_button(self):
        invoice = self.env['account.invoice'].browse(self.invoice_id.id)

        if invoice.type != 'in_invoice':
            raise exceptions.ValidationError(
                "A função Exportar XML deve ser utilizada exclusivamente na Fatura de Fornecedor"
            )

        #Verifica se arquivo é NFe
        ##############################################################################
        decode = base64.b64decode(self.xml)
        arquivo = BytesIO(decode)
        try:
            nota = parser.parse(arquivo)
            # nota_completa = xmltodict.parse(decode)
        except:
            raise exceptions.ValidationError("""O arquivo que você importou é imcompatível.
            Tenha certeza de ter importado uma NFe ou NFCe no formato XML""")
        ##############################################################################

        ##############################################################################
        #Verifica se a nota já existe nota com o mesmo número cadastrada no fornecedor
        partner = self.env["res.partner"].search([
            ('cnpj_cpf','=',nota.infNFe.emit.CNPJ)
        ])
        reference = False
        if partner:
            reference = self.env['account.invoice'].search([
                ('reference', '=', (nota.infNFe.ide.nNF + "-" + nota.infNFe.ide.serie)),
                ('partner_id', '=', partner.id)
            ])
        if reference:
            raise exceptions.ValidationError("""A nota nº %s relacionada ao fornecedor %s já
            está cadastrada no sistema. Não é permitido o cadastro de notas
            duplicadas para o mesmo fornecedor.""" %(nota.infNFe.ide.nNF, partner.name))
        ##############################################################################

        ##############################################################################
        #Veririca se CNPJ da nota é o mesmo CNPJ da empresa do usuário
        if not self.env.user.company_id.cnpj_cpf:
            raise exceptions.ValidationError("""Não há um CNPJ cadastrado em sua empresa.
            Por favor, cadastre um CNPJ em sua empresa antes de Importar o XML da NFe.""")
        CNPJ = re.sub("\D","", self.env.user.company_id.cnpj_cpf)
        if nota.infNFe.dest.CNPJ != CNPJ and not self.importar_empresa_dif:
            raise exceptions.ValidationError("""O XML importado possui um destinatário com CNPJ
            diferente do CNPJ da sua empresa. Par importar XML com destinatário que seja diferente
            de sua empresa, selecionea opção Forçar importação de empresa diferente da minha.""" )
        ##############################################################################

        ##############################################################################
        #Transfere dados para nota fiscal
        invoice.dados_xml = self.xml
        invoice.atualizar_produtos = self.atualizar_produtos
        invoice.conta_produto_id = self.account_id
        invoice.criar_fornecedor = self.criar_fornecedor
        invoice.criar_transportadora = self.criar_transportadora
        invoice.fornecedor_como_cliente = self.fornecedor_como_cliente
        invoice.criar_produtos = self.criar_produtos
        invoice.account_analytic_id = self.account_analytic_id
        invoice.posicao_fiscal = self.posicao_fiscal
        ##############################################################################

        invoice._compute_dados_xml()
