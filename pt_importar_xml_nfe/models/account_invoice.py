import base64
import xmltodict
import datetime
from io import BytesIO
from nfelib.v4_00 import leiauteNFe_sub as parser
from odoo import models, api, fields,_, exceptions
import odoo.addons.decimal_precision as dp

class AccountInvoice(models.Model):
    _inherit="account.invoice"

    def action_importar_xml_nfe(self):
        return {"type": "ir.actions.act_window",
                "name": _("Importar XML do Fornecedor"),
                "res_model": "importar.xml.nfe",
                "target": "new",
                "view_mode": "form",
                "view_type": "form",
                "context": {"default_invoice_id": self.id},
                }

    def action_excluir_xml(self):
        self.dados_xml = False
        self.reference = ''

    dados_xml = fields.Binary(
        string="Arquivo XML da Nota Fiscal",
        store=True)

    account_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Conta Analítica",
        help="Caso seja selecionada esta conta será utilizada em todas as linhas da fatura")

    criar_fornecedor = fields.Boolean(
        string="Importar/Criar Fornecedor Automaticamente",
        help="Irá criar automaticamente um fornecedor com base nos dados da fatura")

    criar_transportadora = fields.Boolean(
        string="Importar/Criar Transportadora Automaticamente",
        help="Irá criar automaticamente um fornecedor com base nos dados da fatura")

    fornecedor_como_cliente = fields.Boolean(
        string="Marcar Fornecedor como Cliente",
        help="Irá marcar o fornecedor criado como um cliente no sistema para ser utilizado no módulo de vendas")

    criar_produtos = fields.Boolean(
        string="Importar/Criar Produtos Automaticamente",
        help="Irá criar automaticamente produtos com base nos dados da Nota Fiscal.")

    atualizar_produtos = fields.Boolean(
        string="Atualizar produtos existentes",
        help="Irá substituir os dados dos  produtos cadastrados no fornecedor, caso existam.")

    conta_produto_id = fields.Many2one(
        "account.account",
        string="Conta do Produto",
    )

    posicao_fiscal = fields.Many2one(
        "account.fiscal.position",
        string="Posição Fiscal do XML da NFe")

    ##############################################################################
    #Preenche os dados com base no XML da NFe cadastrada pelo usuário
    @api.multi
    @api.onchange("dados_xml")
    def _compute_dados_xml(self):
        for r in self:
            ##############################################################################
            # Parse xml
            if r.dados_xml:
                decode = base64.b64decode(r.dados_xml)
                arquivo = BytesIO(decode)
                try:
                    nota = parser.parse(arquivo)
                    #Dados no Formato nota.infNFe.ide.nNF
                    nota_completa = xmltodict.parse(decode)
                    #Dados no Formato nota_completa["nfeProc"]["NFe"]["infNFe"]["ide"]["cUF"]
                except:
                    raise exceptions.ValidationError("""O arquivo que você importou é imcompatível.
                    Tenha certeza de ter importado o arquivo correto.""")

                ##############################################################################
                # Inclui cadastros principais na fatura baseados da nota
                self.reference = nota.infNFe.ide.nNF + "-" + nota.infNFe.ide.serie

                ##############################################################################
                # Formata data de emissão da nota
                data_nota = nota.infNFe.ide.dhEmi.split("T")[0]
                self.date_invoice = datetime.datetime.strptime(data_nota,"%Y-%m-%d").date()

                ##############################################################################
                # Informações de Frete e Transportadora
                self.freight_responsibility = nota.infNFe.transp.modFrete
                self.weight = nota.infNFe.transp.vol[0].pesoB if nota.infNFe.transp.vol else ""
                self.weight_net = nota.infNFe.transp.vol[0].pesoL if nota.infNFe.transp.vol else ""
                self.kind_of_packages = nota.infNFe.transp.vol[0].esp if nota.infNFe.transp.vol else ""
                self.number_of_packages = nota.infNFe.transp.vol[0].nVol if nota.infNFe.transp.vol and isinstance(nota.infNFe.transp.vol[0].nVol, int) else ""
                self.brand_of_packages = nota.infNFe.transp.vol[0].marca if nota.infNFe.transp.vol else ""
                # self.notation_of_packages = nota.infNFe.transp.vol[0]
                self.vehicle_plate = nota.infNFe.transp.veicTransp[0].placa if nota.infNFe.transp.veicTransp else ""
                self.vehicle_state_id = self.env["res.country.state"].search(
                    [("code", "=", nota.infNFe.transp.veicTransp[0].UF if  nota.infNFe.transp.veicTransp else "")]).id
                self.vehicle_rntc = nota.infNFe.transp.veicTransp[0].RNTC if nota.infNFe.transp.veicTransp else ""
                self.tow_plate = nota.infNFe.transp.reboque[0].placa if nota.infNFe.transp.reboque else ""
                self.tow_state_id = self.env["res.country.state"].search(
                    [("code", "=", nota.infNFe.transp.reboque[0].UF if nota.infNFe.transp.reboque else "")]).id
                self.tow_rntc = nota.infNFe.transp.reboque[0].RNTC if nota.infNFe.transp.reboque else ""

                ##############################################################################
                #Biblioteca NFeLib não traz o valor da Chave da NFe
                #Especificamente aqui foi utilizado xmltodict
                self.fiscal_document_related_ids =  [(0, 0, {
                   "document_type":"nfe",
                   "access_key": nota_completa["nfeProc"]["NFe"]["infNFe"]["@Id"].strip("NFe"),
                   })]

                self.fiscal_comment = nota.infNFe.infAdic.infCpl if nota.infNFe.infAdic else ""

                ##############################################################################
                #Versões Futuras
                #Valores totais da Nota fiscal
                #self.total_desconto = nota.infNFe.total.ICMSTot.vDesc
                # self.total_despesas =
                # self.total_seguro =
                # self.total_frete =
                # self.total_despesas_aduana =

                ##############################################################################
                # Verifica se há Transportadora cadastrada com o CNPJ da nota
                # Só executa se houver transportadora na nota fiscal
                if self.criar_transportadora and nota.infNFe.transp.transporta:
                    transportadora_existente = self.env["res.partner"].search([
                    ("cnpj_cpf", "=", nota.infNFe.transp.transporta.CNPJ)
                    ])
                    if transportadora_existente:
                        self.shipping_supplier_id = transportadora_existente.id

                    ##############################################################################
                    # Realiza o cadastro da Transportadora e o vincula à fatura caso ainda não haja cadastro
                    else:
                        vals = {
                            "type": "contact",
                            "supplier":True,
                            "name": nota.infNFe.transp.transporta.xNome,
                            "legal_name": nota.infNFe.transp.transporta.xNome,
                            "cnpj_cpf": nota.infNFe.transp.transporta.CNPJ,
                            "is_company": "True",
                            "street": nota.infNFe.transp.transporta.xEnder,
                            "inscr_est": nota.infNFe.transp.transporta.IE,
                        }
                        transportadora_nova_id = self.env["res.partner"].create(vals)
                        self.shipping_supplier_id = transportadora_nova_id

                ##############################################################################
                # Verifica se já existe fornecedor cadastrado com o CNPJ da nota
                if self.criar_fornecedor:
                    fornecedor_existente = self.env["res.partner"].search([("cnpj_cpf","=",nota.infNFe.emit.CNPJ)])

                    if fornecedor_existente:
                        self.partner_id = fornecedor_existente.id
                        self.account_id = fornecedor_existente.property_account_payable_id
                    ##############################################################################
                   # Realiza o cadastro do fornecedor e o vincula à fatura.
                    else:
                        vals = {
                            "type": "contact",
                            "supplier": True,
                            "name": nota.infNFe.emit.xFant if nota.infNFe.emit.xFant else nota.infNFe.emit.xNome,
                            "legal_name": nota.infNFe.emit.xNome,
                            "cnpj_cpf": nota.infNFe.emit.CNPJ,
                            "is_company": "True",
                            "zip": nota.infNFe.emit.enderEmit.CEP,
                            "state_id": self.env["res.country.state"].search(
                                [("code", "=", nota.infNFe.emit.enderEmit.UF)]).id,
                            #Código de município trazido pela NFe não é o mesmo utilizado pela Trustcode
                            #Dessa forma, o código esta pesquisando a primeira cidade encontrada com o
                            #Mesmo nome utilizado na NFe
                            "city_id": self.env["res.state.city"].search(
                                [("name", "=", nota.infNFe.emit.enderEmit.xMun)], limit=1).id,
                            "street": nota.infNFe.emit.enderEmit.xLgr,
                            "number": nota.infNFe.emit.enderEmit.nro,
                            "district": nota.infNFe.emit.enderEmit.xBairro,
                            "country_id": self.env["res.country"].search(
                                [("bc_code","=",nota.infNFe.emit.enderEmit.cPais)]
                            ),
                            "street2": nota.infNFe.emit.enderEmit.xCpl if nota.infNFe.emit.enderEmit.xCpl else "",
                            "phone": nota.infNFe.emit.enderEmit.fone,
                            "inscr_est": nota.infNFe.emit.IE,
                        }
                        fornecedor_novo_id = self.env["res.partner"].create(vals)
                        self.partner_id = fornecedor_novo_id
                        self.account_id = fornecedor_novo_id.property_account_payable_id

                ##############################################################################
                #Cadastro dos produtos no Odoo caso seja a escolha do usuário
                index = -1
                for produto in nota.infNFe.det:
                    index += 1
                    produto_existente = self.env["product.product"].search([("default_code", "=", produto.prod.cProd)])
                    produto_existe = False
                    id_existente = False
                    produto_novo = False
                    #Verifica se o produto já existe naquele fornecedor
                    if produto_existente:
                        for prd in produto_existente:
                            if prd.seller_ids:
                                if any(i.name.cnpj_cpf for i in prd.seller_ids):
                                    produto_existe = True
                                    id_existente = prd.id

                    ##############################################################################
                    #Atualiza produto caso já exista
                    #Verifica se o usuário marcou a opção de atualizar o produto
                    if produto_existe:
                        if self.atualizar_produtos:
                            vals = {
                                "name": produto.prod.xProd,
                                "default_code": produto.prod.cProd,
                                "fiscal_classification_id":self.env["product.fiscal.classification"].search([("code","=",produto.prod.NCM)]).id,
                                "cest": produto.prod.CEST,
                                "origin": produto.imposto.ICMS.ICMS00.orig if produto.imposto.ICMS else "",
                                "fiscal_type": "service" if produto.prod.NCM == "00" else "product",
                                "type": "service" if produto.prod.NCM == "00" else "product",
                                #"service_type_id": "",
                                "standard_price":round(float(produto.prod.vUnCom),2),
                            }
                            produto_existente.update(vals)

                    ##############################################################################
                    #Cria os produtos, caso o usuário tenha marcado essa opção
                    else:
                        if self.criar_produtos:
                            vals = {
                                "name": produto.prod.xProd,
                                "default_code": produto.prod.cProd,
                                "sale_ok": False,
                                "purchase_ok": True,
                                "fiscal_type": "service" if produto.prod.NCM == "00" else "product",
                                "fiscal_classification_id": self.env["product.fiscal.classification"].search([("code","=",produto.prod.NCM)]).id if produto.prod.NCM != "00" else '',
                                "service_type_id": produto.imposto.ISSQN.cListServ if produto.imposto.ISSQN else "",
                                "cnpj_cpf": nota.infNFe.emit.CNPJ,
                                "cest": produto.prod.CEST,
                                "origin": produto.imposto.ICMS.ICMS00.orig if produto.imposto.ICMS else "",
                                "type": "service" if produto.prod.NCM == "00" else "product",
                                "service_type_id": "",
                                "standard_price":round(float(produto.prod.vUnCom),2),
                                "seller_ids": [(0, 0, {"name": self.partner_id.id,
                                                       "product_name": produto.prod.xProd,
                                                       "product_code": produto.prod.cProd,
                                                       "price": produto.prod.vProd,
                                                       })]
                                }
                            produto_novo = self.env["product.product"].create(vals)

                    ##############################################################################
                    #Armazena o ID do produto que será utilizado na fatura
                    produto_fatura = produto_novo.id if produto_novo else id_existente

                    ##############################################################################
                    #Pesquisa NCM do produto em diversos casos
                    def ncm_produto():
                        id_ncm = self.env["product.product"].browse(produto_fatura).fiscal_classification_id.id
                        ncm_produto = ""
                        if produto_fatura and id_ncm:
                            ncm_produto = id_ncm
                        elif produto.prod.NCM  != "00":
                            ncm_produto = self.env["product.fiscal.classification"].search([("code","=",produto.prod.NCM)]).id
                        else:
                             ncm_produto = ""
                        return ncm_produto

                    ##############################################################################
                    #Adiciona linhas na fatura com base nos dados da NFe importada
                    #Utiliza os dados do produto existente, caso presente
                    self.invoice_line_ids = [(0, 0, {
                        "product_id": produto_fatura if self.criar_produtos or self.atualizar_produtos else "",
                        "name": produto.prod.xProd,
                        "cfop_id": self.env["br_account.cfop"].search(
                            [("code","=",produto.prod.CFOP)]
                        ),
                        "tributos_estimados": produto.imposto.vTotTrib,
                        "quantity": produto.prod.qCom,
                        "price_unit": round(float(produto.prod.vUnCom if produto.prod.indTot == '1' else 0.0),2),
                        "discount_fixed":round(float(produto.prod.vDesc if produto.prod.vDesc else 0.0),2),
                        "account_id": self.conta_produto_id.id,
                        "fiscal_classification_id": ncm_produto(),
                        "account_analytic_id": self.account_analytic_id,
                        })]

                    super()._compute_amount()
                    self.invoice_line_ids[index]._compute_price()
                    self.fiscal_position_id = self.posicao_fiscal if self.posicao_fiscal else self.fiscal_position_id

    ##############################################################################################
    # DESCONTO FIXO NA LINHA DA fatura
    ##############################################################################################


    @api.multi
    def get_taxes_values(self):
        self.ensure_one()
        vals = {}
        for line in self.invoice_line_ids.filtered('discount_fixed'):
            vals[line] = {
                # 'price_unit': line.price_unit,
                # 'discount_fixed': line.discount_fixed,
                'price_subtotal': (line.price_unit * line.quantity) - line.discount_fixed
            }
            price_unit = line.price_unit - line.discount_fixed
            price_subtotal = (line.price_unit * line.quantity) - line.discount_fixed
            line.update({
                # 'price_unit': price_unit,
                # 'discount_fixed': 0.0,
                'price_subtotal': price_subtotal,
            })
        tax_grouped = super(AccountInvoice, self).get_taxes_values()
        for line in vals.keys():
            line.update(vals[line])
        return tax_grouped


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    discount_fixed = fields.Float(
        string="Desconto (fixo)",
        digits=dp.get_precision('Product Price'),
        help="Desconto Fixo Total.")

    @api.onchange('discount')
    def _onchange_discount(self):
        if self.discount:
            self.discount_fixed = 0.0

    @api.onchange('discount_fixed')
    def _onchange_discount_fixed(self):
        if self.discount_fixed:
            self.discount = 0.0

    @api.multi
    @api.constrains('discount', 'discount_fixed')
    def _check_only_one_discount(self):
        for line in self:
            if line.discount and line.discount_fixed:
                raise exceptions.ValidationError(
                    _("Você só pode aplicar um tipo de desconto por linha."))

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id',
                 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date',
                 'discount_fixed')
    def _compute_price(self):
        if not self.discount_fixed:
            return super(AccountInvoiceLine, self)._compute_price()
        prev_price_unit = self.price_unit
        prev_discount_fixed = self.discount_fixed
        price_unit = self.price_unit - self.discount_fixed
        # price_subtotal = (self.price_unit * self.quantity) - self.discount_fixed
        self.update({
            'price_unit': price_unit,
            'discount_fixed': 0.0,
            # 'price_subtotal': price_subtotal,
        })
        super(AccountInvoiceLine, self)._compute_price()
        self.update({
            'price_unit': prev_price_unit,
            'discount_fixed': prev_discount_fixed,
        })
