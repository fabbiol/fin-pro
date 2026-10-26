"""Planilha Excel (.xlsx) usada como banco de dados.

Abas:
* **Boletos** — um boleto por linha, com filtros, validação de status e destaque de vencidos/pagos;
* **Pix** — pagamentos por Pix (tipo e chave, valor, recebedor, data prevista...);
* **Resumo** — fórmulas que o Excel recalcula ao abrir (totais, vencidos...);
* **Centros de Custo** — onde cada gasto foi feito (usado na análise de gastos);
* **Histórico** — registro de cada lançamento, edição, pagamento, comprovante e exclusão, com o usuário que fez.

Gravações são atômicas (salva em arquivo temporário e substitui), agrupadas em lote e com backup diário.
Se a planilha estiver aberta no Excel, a gravação falha com ``PlanilhaBloqueadaError`` — a fila de
gravação guarda as operações e grava quando o arquivo for fechado.
"""

from __future__ import annotations

import os
import re
import shutil
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from .importacao import ler_valor

ABA_BOLETOS = "Boletos"
ABA_PIX = "Pix"
ABA_RESUMO = "Resumo"
ABA_CENTROS = "Centros de Custo"
ABA_HISTORICO = "Histórico"
ABA_CAIXA = "Caixa"
COLUNAS_HISTORICO = [("Data/Hora", 18), ("Ação", 18), ("ID", 7), ("Beneficiário / Recebedor", 40), ("Vencimento", 13),
                     ("Valor (R$)", 14), ("Detalhes", 60), ("Usuário", 22)]
STATUS_VALIDOS = ("Pendente", "Pago", "Cancelado")
TIPOS = {"bancario": "Bancário", "arrecadacao": "Arrecadação"}
TIPOS_CHAVE = {"cpf_cnpj": "CNPJ/CPF", "celular": "Celular", "email": "E-mail", "aleatoria": "Aleatória"}
ROTULOS = {"tipo": TIPOS, "tipo_chave": TIPOS_CHAVE}
LINHAS_FORMATADAS = 20000
BACKUPS_MANTIDOS = 30
COR_CABECALHO = "0F3D3E"
COR_FAIXA = "F3F7F7"

CENTROS_PADRAO = [
    ("Administrativo", "Escritório, contabilidade, bancos e despesas gerais"),
    ("Produção", "Matéria-prima, insumos e serviços da produção"),
    ("Obras", "Materiais e serviços aplicados em obras"),
    ("Combustível e Veículos", "Combustível, lubrificantes, peças e manutenção da frota"),
    ("Manutenção", "Máquinas, equipamentos e instalações"),
    ("Impostos e Taxas", "Tributos, guias e taxas"),
    ("Energia, Água e Telefone", "Contas de consumo"),
    ("Pessoal", "Salários, benefícios e encargos"),
    ("Outros", ""),
]


@dataclass(frozen=True)
class Coluna:
    chave: str
    titulo: str
    largura: int
    formato: str | None = None


COLUNAS: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data_lancamento", "Data de Lançamento", 19, "dd/mm/yyyy hh:mm"),
    Coluna("linha_digitavel", "Linha Digitável", 58, "@"),
    Coluna("codigo_barras", "Código de Barras", 48, "@"),
    Coluna("beneficiario", "Beneficiário", 42),
    Coluna("documento_beneficiario", "CPF/CNPJ Beneficiário", 21, "@"),
    Coluna("numero_documento", "Nº do Documento", 18, "@"),
    Coluna("vencimento", "Vencimento", 13, "dd/mm/yyyy"),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("emissor", "Banco / Segmento", 26),
    Coluna("tipo", "Tipo", 13),
    Coluna("status", "Status", 12),
    Coluna("data_pagamento", "Data de Pagamento", 17, "dd/mm/yyyy"),
    Coluna("valor_pago", "Valor Pago (R$)", 15, '"R$" #,##0.00'),
    Coluna("juros_multa", "Juros/Multa (R$)", 15, '"R$" #,##0.00'),
    Coluna("desconto", "Desconto (R$)", 14, '"R$" #,##0.00'),
    Coluna("observacoes", "Observações", 34),
    Coluna("centro_custo", "Centro de Custo", 26),
    Coluna("arquivo", "Arquivo", 30),
    Coluna("arquivo_nome", "Nome do Arquivo Original", 32),
    Coluna("lancado_por", "Lançado por", 20),
    Coluna("pago_por", "Pago por", 20),
    Coluna("comprovante", "Comprovante", 30),
    Coluna("comprovante_nome", "Nome do Comprovante", 30),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

COLUNAS_PIX: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data_lancamento", "Data de Lançamento", 19, "dd/mm/yyyy hh:mm"),
    Coluna("recebedor", "Recebedor", 38),
    Coluna("tipo_chave", "Tipo da Chave", 14),
    Coluna("chave", "Chave Pix", 38, "@"),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("vencimento", "Data Prevista", 14, "dd/mm/yyyy"),
    Coluna("centro_custo", "Centro de Custo", 26),
    Coluna("descricao", "Descrição", 36),
    Coluna("status", "Status", 12),
    Coluna("data_pagamento", "Data de Pagamento", 17, "dd/mm/yyyy"),
    Coluna("valor_pago", "Valor Pago (R$)", 15, '"R$" #,##0.00'),
    Coluna("juros_multa", "Juros/Multa (R$)", 15, '"R$" #,##0.00'),
    Coluna("desconto", "Desconto (R$)", 14, '"R$" #,##0.00'),
    Coluna("txid", "Identificador (TXID)", 24, "@"),
    Coluna("copia_e_cola", "Pix Copia e Cola", 40, "@"),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Arquivo", 28),
    Coluna("arquivo_nome", "Nome do Arquivo Original", 30),
    Coluna("lancado_por", "Lançado por", 20),
    Coluna("pago_por", "Pago por", 20),
    Coluna("comprovante", "Comprovante", 28),
    Coluna("comprovante_nome", "Nome do Comprovante", 30),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]

CAMPOS_DATA = {"vencimento", "data_pagamento", "data", "data_deposito", "data_recebimento", "data_fechamento"}
CAMPOS_DATA_HORA = {"data_lancamento", "atualizado_em", "data_hora"}
CAMPOS_NUMERO = {"quantidade", "litros", "medidor", "preco_litro"}  # números soltos (quantidade, litros, horímetro…)
# Caixa: dinheiro que entra (o que foi pedido) e que sai (onde foi gasto e em qual centro de custo)
COLUNAS_CAIXA: list[Coluna] = [
    Coluna("id", "ID", 7, "0"),
    Coluna("data", "Data", 12, "dd/mm/yyyy"),
    Coluna("hora", "Hora", 8, "@"),
    Coluna("movimento", "Entrada/Saída", 13),
    Coluna("valor", "Valor (R$)", 15, '"R$" #,##0.00'),
    Coluna("descricao", "O que foi pedido / comprado", 40),
    Coluna("local", "Onde foi gasto", 30),
    Coluna("centro_custo", "Centro de Custo", 26),
    Coluna("pessoa", "Quem", 20),
    Coluna("status", "Situação", 12),
    Coluna("observacoes", "Observações", 30),
    Coluna("arquivo", "Comprovante", 28),
    Coluna("arquivo_nome", "Nome do Comprovante", 30),
    Coluna("lancado_por", "Lançado por", 20),
    Coluna("data_lancamento", "Data de Lançamento", 19, "dd/mm/yyyy hh:mm"),
    Coluna("atualizado_em", "Atualizado em", 19, "dd/mm/yyyy hh:mm"),
]
MOVIMENTOS_CAIXA = ("Entrada", "Saída")

CAMPOS_AUTORIA = frozenset({"lancado_por", "pago_por"})  # preenchidos pelo sistema, nunca pela tela
CAMPOS_COMPROVANTE = frozenset({"comprovante", "comprovante_nome"})
TEXTOS_COMUNS = CAMPOS_AUTORIA | CAMPOS_COMPROVANTE
CAMPOS_PAGAMENTO = frozenset({"valor_pago", "juros_multa", "desconto"})  # preenchidos pelo comprovante ou à mão
CAMPOS_MOEDA = {"valor", "valor_unitario", "valor_total", "valor_recebido"} | CAMPOS_PAGAMENTO


@dataclass(frozen=True)
class DefinicaoAba:
    chave: str
    nome: str
    colunas: tuple[Coluna, ...]
    editaveis: frozenset[str]
    campo_nome: str  # quem recebe o pagamento (usado no Histórico)
    textos: frozenset[str]  # campos lidos como "" quando vazios
    cor: str
    sufixo_acao: str
    status_validos: tuple[str, ...] = STATUS_VALIDOS
    campo_data: str = "vencimento"  # data usada no destaque de atrasados e no Histórico
    status_ok: str = "Pago"  # status pintado de verde na planilha ("" = nenhum)
    status_cancelado: str = "Cancelado"  # status riscado na planilha ("" = nenhum)

    @property
    def por_chave(self) -> dict[str, Coluna]:
        return {c.chave: c for c in self.colunas}

    @property
    def status_padrao(self) -> str:
        return self.status_validos[0]

    def tem(self, chave: str) -> bool:
        return any(c.chave == chave for c in self.colunas)

    def letra(self, chave: str) -> str:
        return get_column_letter([c.chave for c in self.colunas].index(chave) + 1)


ABAS: dict[str, DefinicaoAba] = {
    "boletos": DefinicaoAba(
        "boletos", ABA_BOLETOS, tuple(COLUNAS),
        frozenset({"linha_digitavel", "codigo_barras", "beneficiario", "documento_beneficiario", "numero_documento", "vencimento",
                   "valor", "emissor", "tipo", "status", "data_pagamento", "observacoes", "centro_custo", "arquivo", "arquivo_nome"})
        | CAMPOS_COMPROVANTE | CAMPOS_PAGAMENTO,
        "beneficiario", frozenset({"beneficiario", "observacoes", "numero_documento", "centro_custo"}) | TEXTOS_COMUNS, COR_CABECALHO, "",
    ),
    "pix": DefinicaoAba(
        "pix", ABA_PIX, tuple(COLUNAS_PIX),
        frozenset({"recebedor", "tipo_chave", "chave", "valor", "vencimento", "centro_custo", "descricao", "status",
                   "data_pagamento", "txid", "copia_e_cola", "observacoes", "arquivo", "arquivo_nome"}) | CAMPOS_COMPROVANTE | CAMPOS_PAGAMENTO,
        "recebedor", frozenset({"recebedor", "descricao", "observacoes", "centro_custo", "txid"}) | TEXTOS_COMUNS, "1F5FA8", " (Pix)",
    ),
}

ABAS["caixa"] = DefinicaoAba(
    "caixa", ABA_CAIXA, tuple(COLUNAS_CAIXA),
    frozenset({"data", "hora", "movimento", "valor", "descricao", "local", "centro_custo", "pessoa", "status",
               "observacoes", "arquivo", "arquivo_nome"}),
    "descricao", frozenset({"descricao", "local", "centro_custo", "pessoa", "observacoes", "hora", "movimento",
                            "arquivo", "arquivo_nome", "lancado_por"}),
    "8A5200", " (Caixa)", ("Confirmado", "Cancelado"), "data", "", "Cancelado",
)

# Compatibilidade com o restante da aplicação (aba de boletos)
COLUNA_POR_CHAVE = ABAS["boletos"].por_chave
CAMPOS_EDITAVEIS = set(ABAS["boletos"].editaveis)


class PlanilhaBloqueadaError(RuntimeError):
    """A planilha está aberta/bloqueada por outro programa."""


class RegistroNaoEncontrado(KeyError):
    pass


def _letra(chave: str) -> str:
    return ABAS["boletos"].letra(chave)


def _estilizar_cabecalho(celula, cor: str) -> None:
    celula.font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    celula.fill = PatternFill("solid", fgColor=cor)
    celula.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


class PlanilhaBoletos:
    def __init__(self, caminho: Path, pasta_backup: Path | None = None, abas: dict[str, DefinicaoAba] | None = None,
                 extras: bool = True):
        """``abas``: conjunto de abas da planilha (padrão: Boletos e Pix). ``extras``: criar Resumo e Centros de Custo."""
        self.caminho = Path(caminho)
        self.pasta_backup = Path(pasta_backup) if pasta_backup else None
        self.abas = abas or ABAS
        self.extras = extras
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[int, list]] = {}

    # ------------------------------------------------------------------ criação

    def garantir(self) -> None:
        with self._lock:
            if self.caminho.exists():
                return
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            wb = Workbook()
            primeira, *demais = self.abas.values()
            ws = wb.active
            ws.title = primeira.nome
            self._formatar_aba(ws, primeira)
            for definicao in demais:
                self._formatar_aba(wb.create_sheet(definicao.nome), definicao)
            if self.extras:
                self._criar_resumo(wb)
                self._garantir_centros(wb)
            self._salvar(wb, backup=False)

    def migrar(self) -> bool:
        """Planilhas criadas por versões anteriores ganham as abas Pix e Centros de Custo e a coluna Centro de Custo."""
        with self._lock:
            self.garantir()
            if not self.extras:  # outras planilhas (ex.: fechamentos) são sempre geradas do banco
                return False
            wb = load_workbook(self.caminho, read_only=True)
            try:
                faltando = ABA_PIX not in wb.sheetnames or ABA_CENTROS not in wb.sheetnames
                if not faltando and ABA_BOLETOS in wb.sheetnames:
                    cabecalho = next(wb[ABA_BOLETOS].iter_rows(max_row=1, values_only=True), ())
                    faltando = "Centro de Custo" not in cabecalho
            finally:
                wb.close()
            if not faltando:
                return False
            wb = self._abrir_para_escrita()
            if ABA_PIX not in wb.sheetnames:
                indice = wb.sheetnames.index(ABA_BOLETOS) + 1 if ABA_BOLETOS in wb.sheetnames else None
                self._formatar_aba(wb.create_sheet(ABA_PIX, indice), ABAS["pix"])
            if ABA_CENTROS not in wb.sheetnames:
                ws = self._garantir_centros(wb)
                if ABA_HISTORICO in wb.sheetnames:
                    wb.move_sheet(ws, offset=wb.sheetnames.index(ABA_HISTORICO) - wb.sheetnames.index(ABA_CENTROS))
            if ABA_BOLETOS in wb.sheetnames:
                self._garantir_colunas(wb[ABA_BOLETOS], ABAS["boletos"])
            self._salvar(wb)
            return True

    def _formatar_aba(self, ws, definicao: DefinicaoAba) -> None:
        borda = Border(bottom=Side(style="medium", color="0B2B2C"))
        for i, coluna in enumerate(definicao.colunas, start=1):
            celula = ws.cell(row=1, column=i, value=coluna.titulo)
            _estilizar_cabecalho(celula, definicao.cor)
            celula.border = borda
            ws.column_dimensions[get_column_letter(i)].width = coluna.largura
        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "C2"
        ws.sheet_properties.tabColor = definicao.cor
        ultima = get_column_letter(len(definicao.colunas))
        ws.auto_filter.ref = f"A1:{ultima}1"

        if not definicao.tem("status"):
            return
        status = definicao.letra("status")
        faixa = f"A2:{ultima}{LINHAS_FORMATADAS}"
        if definicao.status_ok:
            ws.conditional_formatting.add(
                faixa,
                FormulaRule(formula=[f'${status}2="{definicao.status_ok}"'], font=Font(color="1B7F4B"),
                            fill=PatternFill("solid", fgColor="E7F6EE")),
            )
        if definicao.status_cancelado:
            ws.conditional_formatting.add(
                faixa, FormulaRule(formula=[f'${status}2="{definicao.status_cancelado}"'], font=Font(color="8A8F98", strike=True)))
        if definicao.tem(definicao.campo_data):
            venc = definicao.letra(definicao.campo_data)
            ws.conditional_formatting.add(
                faixa,
                FormulaRule(
                    formula=[f'AND(${status}2="{definicao.status_padrao}",${venc}2<>"",${venc}2<TODAY())'],
                    font=Font(color="B42318", bold=True),
                    fill=PatternFill("solid", fgColor="FDECEA"),
                ),
            )
        validacao = DataValidation(type="list", formula1='"' + ",".join(definicao.status_validos) + '"', allow_blank=True)
        validacao.error = "Use " + ", ".join(definicao.status_validos)
        ws.add_data_validation(validacao)
        validacao.add(f"{status}2:{status}{LINHAS_FORMATADAS}")

    def _criar_resumo(self, wb) -> None:
        ws = wb.create_sheet(ABA_RESUMO)
        ws.sheet_properties.tabColor = "2E9E8F"
        ws.column_dimensions["A"].width = 38
        ws.column_dimensions["B"].width = 22

        def faixa(definicao: DefinicaoAba, chave: str) -> str:
            letra = definicao.letra(chave)
            return f"'{definicao.nome}'!{letra}:{letra}"

        b, p = ABAS["boletos"], ABAS["pix"]
        valor, status, venc, ident, pago = (faixa(b, k) for k in ("valor", "status", "vencimento", "id", "valor_pago"))
        pvalor, pstatus, pvenc, pident, ppago = (faixa(p, k) for k in ("valor", "status", "vencimento", "id", "valor_pago"))
        moeda = '"R$" #,##0.00'
        linhas = [
            ("Resumo dos boletos", None, None),
            ("Boletos lançados", f"=COUNT({ident})", "0"),
            ("Pendentes (quantidade)", f'=COUNTIFS({status},"Pendente")', "0"),
            ("Pendentes (valor)", f'=SUMIFS({valor},{status},"Pendente")', moeda),
            ("Vencidos e não pagos (quantidade)", f'=COUNTIFS({status},"Pendente",{venc},"<"&TODAY())', "0"),
            ("Vencidos e não pagos (valor)", f'=SUMIFS({valor},{status},"Pendente",{venc},"<"&TODAY())', moeda),
            ("Vencem nos próximos 7 dias (valor)",
             f'=SUMIFS({valor},{status},"Pendente",{venc},">="&TODAY(),{venc},"<="&TODAY()+6)', moeda),
            # Pago: o que saiu de fato (valor pago; sem ele, o valor do lançamento), como no Painel.
            ("Pagos (valor)", f'=SUMIFS({pago},{status},"Pago")+SUMIFS({valor},{status},"Pago",{pago},"")', moeda),
            ("Resumo dos Pix", None, None),
            ("Pix lançados", f"=COUNT({pident})", "0"),
            ("Pix pendentes (valor)", f'=SUMIFS({pvalor},{pstatus},"Pendente")', moeda),
            ("Pix atrasados (valor)", f'=SUMIFS({pvalor},{pstatus},"Pendente",{pvenc},"<"&TODAY())', moeda),
            ("Pix pagos (valor)", f'=SUMIFS({ppago},{pstatus},"Pago")+SUMIFS({pvalor},{pstatus},"Pago",{ppago},"")', moeda),
        ]
        for i, (titulo, formula, formato) in enumerate(linhas, start=1):
            a = ws.cell(row=i, column=1, value=titulo)
            if formula is None:
                a.font = Font(bold=True, size=14, color=COR_CABECALHO)
                ws.row_dimensions[i].height = 26
                continue
            a.font = Font(color="333333")
            c = ws.cell(row=i, column=2, value=formula)
            c.number_format = formato
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="right")
            if i % 2 == 0:
                a.fill = c.fill = PatternFill("solid", fgColor=COR_FAIXA)

    @staticmethod
    def _garantir_centros(wb):
        if ABA_CENTROS in wb.sheetnames:
            return wb[ABA_CENTROS]
        ws = wb.create_sheet(ABA_CENTROS)
        ws.sheet_properties.tabColor = "A86200"
        for i, (titulo, largura) in enumerate([("Centro de Custo", 30), ("Descrição", 52), ("Ativo", 9), ("Criado em", 18)], start=1):
            _estilizar_cabecalho(ws.cell(row=1, column=i, value=titulo), "8A5200")
            ws.column_dimensions[get_column_letter(i)].width = largura
        ws.freeze_panes = "A2"
        agora = datetime.now().replace(second=0, microsecond=0)
        for nome, descricao in CENTROS_PADRAO:
            ws.append([nome, descricao or None, "Sim", agora])
            ws.cell(row=ws.max_row, column=4).number_format = "dd/mm/yyyy hh:mm"
        return ws

    # ------------------------------------------------------------------ leitura

    @staticmethod
    def _converter_leitura(chave: str, valor, definicao: DefinicaoAba | None = None):
        definicao = definicao or ABAS["boletos"]
        if valor is None or valor == "":
            return "" if chave in definicao.textos else None
        if chave in CAMPOS_DATA:
            if isinstance(valor, datetime):
                return valor.date()
            if isinstance(valor, date):
                return valor
            try:
                return datetime.strptime(str(valor).strip(), "%d/%m/%Y").date()
            except ValueError:
                return None
        if chave in CAMPOS_DATA_HORA:
            if isinstance(valor, datetime):
                return valor
            try:
                return datetime.strptime(str(valor).strip(), "%d/%m/%Y %H:%M")
            except ValueError:
                return None
        if chave == "id":
            try:
                return int(valor)
            except (TypeError, ValueError):
                return None
        if chave in CAMPOS_NUMERO:
            if isinstance(valor, (int, float)):
                return round(float(valor), 4)
            # Texto digitado no Excel: "1.234,5" ou "1234.5" (o ponto sozinho é decimal; só some com vírgula ou vários).
            texto = str(valor).replace(" ", "").strip()
            texto = texto.replace(".", "").replace(",", ".") if "," in texto or texto.count(".") > 1 else texto
            try:
                return round(float(texto), 4)
            except ValueError:
                return None
        if chave in CAMPOS_MOEDA:
            if isinstance(valor, (int, float)):
                return round(float(valor), 2)
            return ler_valor(valor)  # "1.234,56", "1234.56" e "1.500" (mil e quinhentos), como na importação
        if chave in ROTULOS:
            texto = str(valor).strip()
            for codigo, rotulo in ROTULOS[chave].items():
                if texto.lower() in (codigo, rotulo.lower()):
                    return codigo
            return texto.lower() or None
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))
        return str(valor).strip()

    def _ler_registros(self, wb, definicao: DefinicaoAba, so_presentes: bool = False) -> list[dict]:
        """Linhas da aba. Com ``so_presentes``, só os campos cujo título está no cabeçalho: coluna renomeada ou apagada
        no Excel fica de fora, em vez de parecer que a pessoa apagou o valor em todas as linhas."""
        if definicao.nome not in wb.sheetnames:
            return []
        linhas = wb[definicao.nome].iter_rows(values_only=True)
        cabecalho = next(linhas, ())
        por_titulo = {c.titulo: c.chave for c in definicao.colunas}
        indices = {por_titulo[t]: i for i, t in enumerate(cabecalho) if t in por_titulo}
        registros = []
        for linha in linhas:
            if not linha or all(v in (None, "") for v in linha):
                continue
            registro = {
                c.chave: self._converter_leitura(
                    c.chave, linha[indices[c.chave]] if c.chave in indices and indices[c.chave] < len(linha) else None, definicao)
                for c in definicao.colunas if not so_presentes or c.chave in indices
            }
            if registro.get("id") is None:
                continue
            if definicao.tem("status") and "status" in registro:
                registro["status"] = (registro["status"] if registro["status"] in definicao.status_validos
                                      else definicao.status_padrao)
            registros.append(registro)
        return registros

    def _ler_com_cache(self, chave_cache: str, leitor) -> list:
        with self._lock:
            self.garantir()
            mtime = self.caminho.stat().st_mtime_ns
            em_cache = self._cache.get(chave_cache)
            if em_cache and em_cache[0] == mtime:
                return [dict(r) for r in em_cache[1]]
            wb = load_workbook(self.caminho, read_only=True, data_only=True)
            try:
                dados = leitor(wb)
            finally:
                wb.close()
            self._cache[chave_cache] = (mtime, dados)
            return [dict(r) for r in dados]

    def listar(self, aba: str = "boletos") -> list[dict]:
        definicao = self.abas[aba]
        return self._ler_com_cache(aba, lambda wb: self._ler_registros(wb, definicao))

    def listar_como_esta(self, aba: str = "boletos") -> list[dict]:
        """Como ``listar``, mas só com as colunas que existem no arquivo (para trazer edições feitas no Excel)."""
        definicao = self.abas[aba]
        return self._ler_com_cache(aba + ":presentes", lambda wb: self._ler_registros(wb, definicao, so_presentes=True))

    def obter(self, id_: int, aba: str = "boletos") -> dict:
        for registro in self.listar(aba):
            if registro["id"] == id_:
                return registro
        raise RegistroNaoEncontrado(id_)

    def buscar_por_codigo(self, codigo_barras: str) -> list[dict]:
        if not codigo_barras:
            return []
        return [r for r in self.listar() if r.get("codigo_barras") == codigo_barras and r.get("status") != "Cancelado"]

    def nomes_por_documento(self) -> dict[str, str]:
        """CPF/CNPJ (somente dígitos) → nome de beneficiário usado no lançamento mais recente."""
        mapa: dict[str, str] = {}
        ordenados = sorted(self.listar(), key=lambda r: r.get("atualizado_em") or r.get("data_lancamento") or datetime.min)
        for r in ordenados:
            documento = re.sub(r"\D", "", r.get("documento_beneficiario") or "")
            nome = (r.get("beneficiario") or "").strip()
            if len(documento) in (11, 14) and nome and r.get("status") != "Cancelado":
                mapa[documento] = nome
        return mapa

    def listar_centros(self) -> list[dict]:
        def ler(wb):
            if ABA_CENTROS not in wb.sheetnames:
                return [{"nome": nome, "descricao": descricao, "ativo": True} for nome, descricao in CENTROS_PADRAO]
            centros = []
            for linha in wb[ABA_CENTROS].iter_rows(min_row=2, values_only=True):
                if not linha or not linha[0] or not str(linha[0]).strip():
                    continue
                ativo = str(linha[2] if len(linha) > 2 and linha[2] is not None else "Sim").strip().lower()
                centros.append({
                    "nome": str(linha[0]).strip(),
                    "descricao": str(linha[1] or "").strip() if len(linha) > 1 else "",
                    "ativo": ativo not in ("não", "nao", "n", "false", "0"),
                })
            return centros

        return self._ler_com_cache("__centros__", ler)

    # ------------------------------------------------------------------ escrita

    def _verificar_gravavel(self) -> None:
        try:
            with open(self.caminho, "r+b"):
                pass
        except PermissionError as exc:
            raise PlanilhaBloqueadaError(
                "A planilha está aberta em outro programa (ex.: Excel). Feche o arquivo e tente novamente."
            ) from exc

    def _abrir_para_escrita(self):
        self.garantir()
        self._verificar_gravavel()
        return load_workbook(self.caminho)

    def _preparar_aba(self, wb, definicao: DefinicaoAba):
        if definicao.nome in wb.sheetnames:
            ws = wb[definicao.nome]
        else:
            ws = wb.create_sheet(definicao.nome)
            self._formatar_aba(ws, definicao)
        return ws, self._garantir_colunas(ws, definicao)

    @staticmethod
    def _garantir_colunas(ws, definicao: DefinicaoAba | None = None) -> dict[str, int]:
        definicao = definicao or ABAS["boletos"]
        por_titulo = {c.titulo: c.chave for c in definicao.colunas}
        mapa = {}
        ultima = 0
        for celula in ws[1]:
            if celula.value is not None:
                ultima = max(ultima, celula.column)
            if celula.value in por_titulo:
                mapa[por_titulo[celula.value]] = celula.column
        for coluna in definicao.colunas:
            if coluna.chave not in mapa:
                ultima += 1
                _estilizar_cabecalho(ws.cell(row=1, column=ultima, value=coluna.titulo), definicao.cor)
                ws.column_dimensions[get_column_letter(ultima)].width = coluna.largura
                mapa[coluna.chave] = ultima
        return mapa

    @staticmethod
    def _indice_linhas(ws, mapa: dict[str, int]) -> dict[int, int]:
        """ID → número da linha (leitura em bloco, bem mais rápida que célula a célula)."""
        coluna = mapa["id"]
        indice = {}
        for numero, (valor,) in enumerate(ws.iter_rows(min_row=2, min_col=coluna, max_col=coluna, values_only=True), start=2):
            try:
                if valor not in (None, ""):
                    indice[int(valor)] = numero
            except (TypeError, ValueError):
                continue
        return indice

    def _ler_linha(self, ws, mapa: dict[str, int], linha: int, definicao: DefinicaoAba | None = None) -> dict:
        return {chave: self._converter_leitura(chave, ws.cell(row=linha, column=coluna).value, definicao)
                for chave, coluna in mapa.items()}

    @staticmethod
    def _garantir_historico(wb):
        if ABA_HISTORICO in wb.sheetnames:
            ws = wb[ABA_HISTORICO]
            for i, (titulo, largura) in enumerate(COLUNAS_HISTORICO, start=1):
                if ws.cell(row=1, column=i).value in (None, ""):  # planilhas antigas: sem a coluna Usuário
                    _estilizar_cabecalho(ws.cell(row=1, column=i, value=titulo), "4A5A66")
                    ws.column_dimensions[get_column_letter(i)].width = largura
            return ws
        ws = wb.create_sheet(ABA_HISTORICO)
        ws.sheet_properties.tabColor = "7D8B95"
        for i, (titulo, largura) in enumerate(COLUNAS_HISTORICO, start=1):
            _estilizar_cabecalho(ws.cell(row=1, column=i, value=titulo), "4A5A66")
            ws.column_dimensions[get_column_letter(i)].width = largura
        ws.freeze_panes = "A2"
        return ws

    @staticmethod
    def _registrar_historico(ws, quando: datetime, acao: str, registro: dict, detalhes: str = "", campo_nome: str = "beneficiario",
                             usuario: str = "", campo_data: str = "vencimento", campo_valor: str = "valor") -> None:
        ws.append([quando, acao, registro.get("id"), registro.get(campo_nome) or "", registro.get(campo_data),
                   registro.get(campo_valor), detalhes, usuario or None])
        linha = ws._current_row  # a linha recém-acrescentada; ws.max_row percorre a aba inteira a cada chamada
        ws.cell(row=linha, column=1).number_format = "dd/mm/yyyy hh:mm"
        ws.cell(row=linha, column=5).number_format = "dd/mm/yyyy"
        ws.cell(row=linha, column=6).number_format = '"R$" #,##0.00'

    @staticmethod
    def _descrever_alteracoes(antes: dict, dados: dict, definicao: DefinicaoAba | None = None) -> tuple[str, str]:
        por_chave = (definicao or ABAS["boletos"]).por_chave
        mudancas = []
        comprovante = False
        for chave, novo in dados.items():
            if chave == "atualizado_em" or chave not in por_chave or chave in CAMPOS_AUTORIA:
                continue
            if chave in CAMPOS_COMPROVANTE:
                comprovante = comprovante or (antes.get(chave) or None) != (novo or None)
                continue
            anterior = antes.get(chave)
            if (anterior or None) == (novo or None):
                continue
            formatar = lambda v: (v.strftime("%d/%m/%Y") if isinstance(v, date) else "—" if v in (None, "")  # noqa: E731
                                  else f"{v:.2f}".replace(".", ",") if isinstance(v, float) else str(v))
            mudancas.append(f"{por_chave[chave].titulo}: {formatar(anterior)} → {formatar(novo)}")
        if comprovante:
            texto = f"Comprovante anexado: {dados.get('comprovante_nome') or ''}" if dados.get("comprovante") else "Comprovante removido"
            if not mudancas:
                return "Comprovante", texto
            mudancas.append(texto)
        if "status" in dados and dados["status"] != antes.get("status"):
            acao = "Pagamento" if dados["status"] == "Pago" else "Cancelamento" if dados["status"] == "Cancelado" else "Status"
        else:
            acao = "Edição"
        return acao, "; ".join(mudancas)

    @staticmethod
    def _escrever(ws, linha: int, mapa: dict[str, int], dados: dict, definicao: DefinicaoAba | None = None) -> None:
        por_chave = (definicao or ABAS["boletos"]).por_chave
        for chave, valor in dados.items():
            if chave not in mapa:
                continue
            coluna = por_chave[chave]
            if chave in ROTULOS and valor in ROTULOS[chave]:
                valor = ROTULOS[chave][valor]
            if valor == "":
                valor = None
            celula = ws.cell(row=linha, column=mapa[chave])
            celula.value = valor  # ws.cell(..., value=None) não apagaria o conteúdo anterior
            if coluna.formato:
                celula.number_format = coluna.formato
            if chave == "arquivo" and valor:
                # Link relativo à pasta da planilha: clicar no Excel abre o arquivo original
                celula.hyperlink = str(valor)
                celula.font = Font(color="0563C1", underline="single")
            if chave in CAMPOS_MOEDA or chave in ("vencimento", "status", "id", "data_lancamento"):
                celula.alignment = Alignment(horizontal="right" if chave in CAMPOS_MOEDA else "center")

    def aplicar_lote(self, operacoes: list[dict]) -> list[dict]:
        """Aplica várias operações abrindo e salvando a planilha uma única vez.

        Cada operação: ``{"tipo": "adicionar"|"atualizar"|"excluir", "aba": "boletos"|"pix", "id": 3, "dados": {...}}``
        (``aba`` padrão: boletos). Devolve, na mesma ordem, ``{"ok": True, "registro": {...}}`` ou
        ``{"ok": False, "erro": "..."}``. Mudanças vão para a aba Histórico; centros de custo novos são cadastrados.
        """
        if not operacoes:
            return []
        with self._lock:
            wb = self._abrir_para_escrita()
            historico = self._garantir_historico(wb)
            agora = datetime.now().replace(second=0, microsecond=0)
            abas: dict[str, dict] = {}
            centros: dict[str, object] = {}

            def estado_da_aba(chave: str) -> dict:
                if chave not in abas:
                    definicao = self.abas[chave]
                    ws, mapa = self._preparar_aba(wb, definicao)
                    linhas = self._indice_linhas(ws, mapa)
                    abas[chave] = {"definicao": definicao, "ws": ws, "mapa": mapa, "linhas": linhas,
                                   "ultima": max(linhas.values(), default=1), "proximo": max(linhas, default=0) + 1,
                                   "excluir": []}
                return abas[chave]

            def garantir_centro(nome) -> None:
                nome = (nome or "").strip() if isinstance(nome, str) else ""
                if not nome:
                    return
                if "ws" not in centros:
                    centros["ws"] = self._garantir_centros(wb)
                    centros["nomes"] = {str(l[0]).strip().lower() for l in centros["ws"].iter_rows(min_row=2, values_only=True) if l and l[0]}
                if nome.lower() not in centros["nomes"]:
                    centros["ws"].append([nome, None, "Sim", agora])
                    centros["ws"].cell(row=centros["ws"].max_row, column=4).number_format = "dd/mm/yyyy hh:mm"
                    centros["nomes"].add(nome.lower())

            resultados: list[dict] = []
            for operacao in operacoes:
                chave_aba = operacao.get("aba") or next(iter(self.abas))
                if chave_aba not in self.abas:
                    resultados.append({"ok": False, "erro": "aba_invalida"})
                    continue
                estado = estado_da_aba(chave_aba)
                definicao, ws, mapa, linhas = estado["definicao"], estado["ws"], estado["mapa"], estado["linhas"]
                tipo = operacao.get("tipo")
                usuario = str(operacao.get("usuario") or "")[:60]
                dados = {k: v for k, v in (operacao.get("dados") or {}).items() if k in definicao.editaveis}

                if tipo == "adicionar":
                    registro = {c.chave: None for c in definicao.colunas}
                    registro.update(dados)
                    registro.update(id=estado["proximo"], data_lancamento=agora, atualizado_em=agora, lancado_por=usuario)
                    if definicao.tem("status"):
                        registro["status"] = registro.get("status") or definicao.status_padrao
                    if definicao.tem("pago_por"):
                        registro["pago_por"] = usuario if registro.get("status") == "Pago" else None
                    estado["ultima"] += 1
                    self._escrever(ws, estado["ultima"], mapa, registro, definicao)
                    linhas[estado["proximo"]] = estado["ultima"]
                    estado["proximo"] += 1
                    garantir_centro(registro.get("centro_custo"))
                    if chave_aba == "pix":
                        detalhe = f"{TIPOS_CHAVE.get(registro.get('tipo_chave'), '')}: {registro.get('chave') or ''}"
                    else:
                        detalhe = registro.get("linha_digitavel") or ""
                    self._registrar_historico(historico, agora, "Lançamento" + definicao.sufixo_acao, registro, detalhe, definicao.campo_nome,
                                             usuario)
                    resultados.append({"ok": True, "registro": registro})
                elif tipo == "atualizar":
                    linha = linhas.get(operacao.get("id"))
                    if linha is None:
                        resultados.append({"ok": False, "erro": "nao_encontrado"})
                        continue
                    antes = self._ler_linha(ws, mapa, linha, definicao)
                    if definicao.tem("pago_por") and "status" in dados and dados["status"] != antes.get("status"):
                        dados["pago_por"] = usuario if dados["status"] == "Pago" else None
                    dados["atualizado_em"] = agora
                    self._escrever(ws, linha, mapa, dados, definicao)
                    depois = {**antes, **dados}
                    garantir_centro(dados.get("centro_custo"))
                    acao, detalhes = self._descrever_alteracoes(antes, dados, definicao)
                    self._registrar_historico(historico, agora, acao + definicao.sufixo_acao, depois, detalhes, definicao.campo_nome, usuario)
                    resultados.append({"ok": True, "registro": depois})
                elif tipo == "excluir":
                    linha = linhas.pop(operacao.get("id"), None)
                    if linha is None:
                        resultados.append({"ok": False, "erro": "nao_encontrado"})
                        continue
                    registro = self._ler_linha(ws, mapa, linha, definicao)
                    estado["excluir"].append(linha)
                    detalhe = registro.get("linha_digitavel") or registro.get("chave") or ""
                    self._registrar_historico(historico, agora, "Exclusão" + definicao.sufixo_acao, registro, detalhe, definicao.campo_nome,
                                             usuario)
                    resultados.append({"ok": True, "registro": registro})
                else:
                    resultados.append({"ok": False, "erro": "operacao_invalida"})

            for estado in abas.values():
                ws = estado["ws"]
                for linha in sorted(estado["excluir"], reverse=True):
                    ws.delete_rows(linha)
                ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{max(ws.max_row, 2)}"
            self._salvar(wb)
        return resultados

    def adicionar(self, dados: dict, aba: str = "boletos", usuario: str = "") -> dict:
        return self.aplicar_lote([{"tipo": "adicionar", "aba": aba, "dados": dados, "usuario": usuario}])[0]["registro"]

    def adicionar_lote(self, lista: list[dict], aba: str = "boletos", usuario: str = "") -> list[dict]:
        return [r["registro"] for r in self.aplicar_lote(
            [{"tipo": "adicionar", "aba": aba, "dados": d, "usuario": usuario} for d in lista])]

    def atualizar(self, id_: int, alteracoes: dict, aba: str = "boletos", usuario: str = "") -> dict:
        resultado = self.aplicar_lote([{"tipo": "atualizar", "aba": aba, "id": id_, "dados": alteracoes, "usuario": usuario}])[0]
        if not resultado["ok"]:
            raise RegistroNaoEncontrado(id_)
        return resultado["registro"]

    def excluir(self, id_: int, aba: str = "boletos", usuario: str = "") -> None:
        if not self.aplicar_lote([{"tipo": "excluir", "aba": aba, "id": id_, "usuario": usuario}])[0]["ok"]:
            raise RegistroNaoEncontrado(id_)

    def historico_do_registro(self, id_: int, aba: str = "boletos", desde: datetime | None = None) -> list[dict]:
        """Eventos da aba Histórico de um boleto ou Pix, do mais recente para o mais antigo.

        IDs de registros excluídos podem ser reaproveitados: eventos anteriores ao lançamento atual são ignorados.
        """
        pix = bool(self.abas[aba].sufixo_acao)

        def ler(wb):
            if ABA_HISTORICO not in wb.sheetnames:
                return []
            eventos = []
            for linha in wb[ABA_HISTORICO].iter_rows(min_row=2, values_only=True):
                if not linha or len(linha) < 3:
                    continue
                eventos.append({"quando": linha[0], "acao": str(linha[1] or ""), "id": linha[2],
                                "detalhes": str(linha[6] or "") if len(linha) > 6 else "",
                                "usuario": str(linha[7] or "") if len(linha) > 7 else ""})
            return eventos

        limite = desde.replace(second=0, microsecond=0) if isinstance(desde, datetime) else None
        saida = []
        for evento in self._ler_com_cache("__historico__", ler):
            try:
                if int(evento["id"]) != id_:
                    continue
            except (TypeError, ValueError):
                continue
            acao = evento["acao"]
            if acao.endswith(" (Pix)") != pix or acao == "Centro de custo":
                continue
            quando = evento["quando"] if isinstance(evento["quando"], datetime) else None
            if limite and quando and quando < limite:
                continue
            saida.append({"quando": quando.isoformat(timespec="minutes") if quando else None,
                          "acao": acao.removesuffix(" (Pix)"), "detalhes": evento["detalhes"], "usuario": evento["usuario"]})
        saida.reverse()
        return saida

    def salvar_centro(self, nome: str, descricao: str = "", ativo: bool = True, nome_anterior: str | None = None,
                      usuario: str = "") -> dict:
        """Cria ou altera um centro de custo. Renomear atualiza os boletos e Pix que já usavam o nome antigo."""
        nome = (nome or "").strip()
        descricao = (descricao or "").strip()
        if not nome or len(nome) > 60:
            raise ValueError("Informe o nome do centro de custo (até 60 caracteres).")
        with self._lock:
            wb = self._abrir_para_escrita()
            ws = self._garantir_centros(wb)
            historico = self._garantir_historico(wb)
            agora = datetime.now().replace(second=0, microsecond=0)
            linhas = {}
            for numero, linha in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if linha and linha[0] and str(linha[0]).strip():
                    linhas[str(linha[0]).strip().lower()] = numero

            if nome_anterior:
                anterior = nome_anterior.strip()
                linha = linhas.get(anterior.lower())
                outra = linhas.get(nome.lower())
                if outra is not None and outra != linha:
                    wb.close()
                    raise ValueError(f'Já existe um centro de custo chamado "{nome}".')
                if linha is None:  # centro usado em lançamentos, mas ainda sem cadastro na aba
                    ws.append([nome, None, None, agora])
                    linha = ws.max_row
                    ws.cell(row=linha, column=4).number_format = "dd/mm/yyyy hh:mm"
                ws.cell(row=linha, column=1, value=nome)
                ws.cell(row=linha, column=2, value=descricao or None)
                ws.cell(row=linha, column=3, value="Sim" if ativo else "Não")
                atualizados = 0
                if anterior != nome:
                    for definicao in self.abas.values():
                        if definicao.nome not in wb.sheetnames:
                            continue
                        aba_ws = wb[definicao.nome]
                        coluna = self._garantir_colunas(aba_ws, definicao)["centro_custo"]
                        for numero in range(2, aba_ws.max_row + 1):
                            celula = aba_ws.cell(row=numero, column=coluna)
                            if isinstance(celula.value, str) and celula.value.strip().lower() == anterior.lower():
                                celula.value = nome
                                atualizados += 1
                    detalhes = f"Renomeado de {anterior} para {nome} ({atualizados} lançamento(s) atualizado(s))"
                else:
                    detalhes = "Dados atualizados" + ("" if ativo else " · desativado")
            else:
                if nome.lower() in linhas:
                    wb.close()
                    raise ValueError(f'Já existe um centro de custo chamado "{nome}".')
                ws.append([nome, descricao or None, "Sim" if ativo else "Não", agora])
                ws.cell(row=ws.max_row, column=4).number_format = "dd/mm/yyyy hh:mm"
                detalhes = "Criado"
            self._registrar_historico(historico, agora, "Centro de custo", {"beneficiario": nome}, detalhes, usuario=usuario)
            self._salvar(wb)
        return {"nome": nome, "descricao": descricao, "ativo": ativo}

    def _salvar(self, wb, backup: bool = True) -> None:
        if backup:
            self._backup_diario()
        temporario = self.caminho.with_name(f".~{self.caminho.stem}.{os.getpid()}.{threading.get_ident()}.tmp.xlsx")
        try:
            wb.save(temporario)
        finally:
            wb.close()
        try:
            os.replace(temporario, self.caminho)
        except PermissionError as exc:
            temporario.unlink(missing_ok=True)
            raise PlanilhaBloqueadaError(
                "A planilha está aberta em outro programa (ex.: Excel). Feche o arquivo e tente novamente."
            ) from exc
        self._cache = {}

    def _backup_diario(self) -> None:
        if not self.pasta_backup or not self.caminho.exists():
            return
        self.pasta_backup.mkdir(parents=True, exist_ok=True)
        destino = self.pasta_backup / f"{self.caminho.stem}-{date.today():%Y-%m-%d}.xlsx"
        if destino.exists():
            return
        shutil.copy2(self.caminho, destino)
        antigos = sorted(self.pasta_backup.glob(f"{self.caminho.stem}-*.xlsx"))
        for arquivo in antigos[:-BACKUPS_MANTIDOS]:
            arquivo.unlink(missing_ok=True)
