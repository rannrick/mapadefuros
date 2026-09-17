# -*- coding: utf-8 -*-
"""
Mapa de Furos - Programacao de sondagens SPT (ABNT NBR 8036:1983)
Interface grafica (Tkinter) sobre o nucleo mapadefuros_core.
"""

import os
import sys
import json
import threading
import traceback
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import mapadefuros_core as core

APP_NOME = "Mapa de Furos"
APP_VERSAO = "1.0.0"


# ---------------------------------------------------------------------------
# utilitarios
# ---------------------------------------------------------------------------

def recurso(*partes):
    """Caminho de arquivo empacotado (funciona no .exe e no codigo-fonte)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *partes)


def br(x, d=2):
    """Numero no padrao brasileiro: 1.202,56"""
    if x is None:
        return "-"
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def num(txt, nome, inteiro=False, obrigatorio=False):
    txt = (txt or "").strip().replace(",", ".")
    if not txt:
        if obrigatorio:
            raise ValueError(f"Informe {nome}.")
        return None
    try:
        v = int(float(txt)) if inteiro else float(txt)
    except ValueError:
        raise ValueError(f"Valor inválido em {nome}: '{txt}'")
    if v <= 0:
        raise ValueError(f"{nome} deve ser maior que zero.")
    return v


def abrir_no_sistema(caminho):
    try:
        if sys.platform.startswith("win"):
            os.startfile(caminho)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
    except Exception as e:
        messagebox.showerror(APP_NOME, f"Não foi possível abrir:\n{caminho}\n\n{e}")


def pasta_padrao():
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    if not os.path.isdir(docs):
        docs = os.path.expanduser("~")
    return os.path.join(docs, "MapaDeFuros")


# ---------------------------------------------------------------------------
# relatorio em texto (ordem do Passo 4 da skill)
# ---------------------------------------------------------------------------

def montar_relatorio(res, ctx):
    L = []
    a = L.append
    hip = "4.1.1.2 - projeção em planta do EDIFÍCIO" if res["tipo_area"] == "edificio" \
        else "4.1.1.3 - área SEM disposição em planta (terreno)"
    a("=" * 72)
    a(f"PROGRAMAÇÃO DE SONDAGENS SPT - ABNT NBR 8036:1983   [{res['tipo_area'].upper()}]")
    a("=" * 72)
    a(f"Arquivo: {res['arquivo']}   Polígono: {res['poligono']} "
      f"({res['poligonos_no_arquivo']} no arquivo)")
    a("")
    a("1. ÁREA E GEOMETRIA")
    a(f"   Área ............. {br(res['area_m2'])} m²  ({br(res['area_ha'], 4)} ha)")
    a(f"   Perímetro ........ {br(res['perimetro_m'])} m   ({res['vertices']} vértices)")
    a(f"   Retângulo circ. .. B = {br(res['B_m'])} m   L = {br(res['L_m'])} m   "
      f"(L/B = {br(res['L_sobre_B'])})")
    a(f"   Zona UTM ......... {res['utm_zona']} (SIRGAS 2000 / WGS84)")
    a(f"   Hipótese adotada . item {hip}")
    if ctx.get("area_declarada"):
        ad = ctx["area_declarada"]
        dif = (res["area_m2"] - ad) / ad * 100
        a(f"   Área declarada ... {br(ad)} m²  -> diferença {br(dif)} %"
          + ("   << CONFERIR" if abs(dif) > 2 else ""))
    a("")
    a("2. NÚMERO DE SONDAGENS")
    a(f"   Mínimo pela norma: {res['n_norma']}   Adotado: {res['n_final']}")
    a(f"   Critério: {res['criterio_numero']}")
    if res["acima_2400_extrapolado"]:
        a("   ATENÇÃO: área > 2.400 m². A norma remete ao plano particular da construção;")
        a("   o número acima é PISO ADOTADO (progressão 1/400 m²), não exigência da norma.")
    if res["n_final"] != res["n_norma"]:
        if ctx.get("n_forcado"):
            a("   Número definido pelo usuário (acima do mínimo é sempre admissível).")
        elif res["tipo_area"] == "terreno":
            a("   Acréscimo sobre o mínimo para atender espaçamento <= 100 m (4.1.1.3).")
        else:
            a("   Número ajustado na locação para cobrir a área (4.1.1.4-a).")
    a("")
    a("3. LOCAÇÃO")
    a(f"   {'Furo':<10}{'Latitude':>14}{'Longitude':>15}{'E (m)':>14}{'N (m)':>15}")
    for s in res["sondagens"]:
        a(f"   {s['id']:<10}{s['lat']:>14.7f}{s['lon']:>15.7f}"
          f"{br(s['E'], 3):>14}{br(s['N'], 3):>15}")
    e = res["espacamento_m"]
    a(f"   Espaçamento entre vizinhos: mín {br(e.get('min'))} m / "
      f"máx {br(e.get('max_vizinho'))} m")
    a(f"   Maior distância de um ponto da área ao furo mais próximo: "
      f"{br(res['dist_max_area_ate_furo_m'])} m")
    a(f"   Recuo da divisa: {br(res['recuo_divisa_m'])} m")
    a(f"   4.1.1.4-b (não alinhadas): {res['check_4_1_1_4_b']}"
      + ("  (posição corrigida)" if res["corrigiu_alinhamento"] else ""))
    if res["check_4_1_1_3_100m"] is not None:
        a(f"   4.1.1.3 (malha <= 100 m): {res['check_4_1_1_3_100m']}")
    a("")
    a("4. PROFUNDIDADE")
    p = res["profundidade"]
    if p["q_kPa"]:
        orig = ctx.get("origem_q", "")
        a(f"   q = {br(p['q_kPa'], 1)} kPa {orig}")
        a(f"   γ = {br(p['gama_kNm3'], 1)} kN/m³ {ctx.get('origem_gama', '')}")
        a(f"   q/(γ·M·B) = {br(p['q_sobre_gama_M_B'], 3)}   (M = 0,10)")
        a(f"   D pelo critério 4.1.2.2 = {br(p['D_criterio_m'])} m   "
          f"D/B = {br(p['D_sobre_B'], 3)}"
          + ("" if p["convergiu"] else "   (NÃO CONVERGIU - conferir no gráfico)"))
        a(f"   Profundidade prevista ADOTADA = {br(p['D_adotada_m'])} m")
    elif p["D_adotada_m"]:
        a(f"   Sem carga informada. Profundidade mínima adotada = {br(p['D_adotada_m'])} m")
    else:
        a("   Carga não informada: profundidade A DEFINIR (informe q ou nº de pavimentos).")
    fund = ctx.get("fundacao")
    if fund == "rasa":
        a("   Fundação rasa: contar a profundidade a partir da cota de apoio prevista,")
        a("   não do fundo de escavação geral (4.1.2.8).")
    elif fund == "profunda":
        a("   Fundação profunda: contar a partir da cota de arrasamento/base prevista,")
        a("   não da superfície do terreno (4.1.2.9).")
    a("   A profundidade é PREVISTA: o furo encerra pelos critérios de parada de")
    a("   campo (4.1.2.6 / 4.1.2.7).")
    a("")
    a("5. RESSALVAS")
    if ctx.get("origem_q", "").startswith("(ESTIM") or ctx.get("origem_gama", "").startswith("(ESTIM"):
        a("   - Valores marcados como ESTIMADOS devem ser confirmados pelo projetista.")
    if res["tipo_area"] == "edificio":
        a("   - O item 4.1.1.2 conta a projeção do EDIFÍCIO, não o lote. Confirme que o")
        a("     polígono representa a edificação.")
    else:
        a("   - Hipótese de área sem implantação definida (viabilidade). Refazer com a")
        a("     projeção do edifício quando houver implantação.")
    a("   - Os mínimos da norma são piso: aumentar o número em aterros, solos moles,")
    a("     encostas ou subsolo heterogêneo (4.1.1.1).")
    a("")
    a("6. ARQUIVOS GERADOS")
    for k, v in res["arquivos"].items():
        a(f"   {k.upper():<7} {v}")
    a("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# aplicacao
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NOME} - NBR 8036:1983  (v{APP_VERSAO})")
        self.geometry("1280x820")
        self.minsize(1000, 680)
        try:
            self.iconbitmap(recurso("assets", "mapadefuros.ico"))
        except Exception:
            pass

        self.resultados = []      # lista de (res, texto)
        self.poligonos = []
        self._img_ref = None

        self._vars()
        self._layout()
        self._alterna_carga()

    # --------------------------------------------------------------- vars
    def _vars(self):
        self.v_arquivo = tk.StringVar()
        self.v_poligono = tk.StringVar(value="Automático (maior área)")
        self.v_tipo = tk.StringVar(value="edificio")
        self.v_area_decl = tk.StringVar()
        self.v_carga = tk.StringVar(value="pavimentos")
        self.v_pav = tk.StringVar()
        self.v_qpav = tk.StringVar(value="12")
        self.v_q = tk.StringVar()
        self.v_gama = tk.StringVar(value="18")
        self.v_gama_inf = tk.BooleanVar(value=False)
        self.v_fund = tk.StringVar(value="não definida")
        self.v_n = tk.StringVar()
        self.v_modo = tk.StringVar(value="auto")
        self.v_recuo = tk.StringVar(value="2,0")
        self.v_profmin = tk.StringVar()
        self.v_prefixo = tk.StringVar(value="SPT")
        self.v_sep = tk.StringVar(value=" - ")
        self.v_dig = tk.StringVar(value="2")
        self.v_saida = tk.StringVar(value=pasta_padrao())
        self.v_status = tk.StringVar(value="Selecione um arquivo KML, KMZ ou CSV.")

    # ------------------------------------------------------------- layout
    def _layout(self):
        estilo = ttk.Style(self)
        try:
            estilo.theme_use("vista" if sys.platform.startswith("win") else "clam")
        except tk.TclError:
            pass
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 10, "bold"))
        estilo.configure("Grande.TButton", font=("Segoe UI", 10, "bold"))

        menu = tk.Menu(self)
        m_arq = tk.Menu(menu, tearoff=0)
        m_arq.add_command(label="Abrir KML/KMZ/CSV...", command=self.escolher_arquivo)
        m_arq.add_command(label="Abrir pasta de saída", command=self.abrir_saida)
        m_arq.add_separator()
        m_arq.add_command(label="Sair", command=self.destroy)
        menu.add_cascade(label="Arquivo", menu=m_arq)
        m_aj = tk.Menu(menu, tearoff=0)
        m_aj.add_command(label="Regras da NBR 8036", command=lambda: self.nb.select(self.tab_norma))
        m_aj.add_command(label="Sobre", command=self.sobre)
        menu.add_cascade(label="Ajuda", menu=m_aj)
        self.config(menu=menu)

        pan = ttk.PanedWindow(self, orient="horizontal")
        pan.pack(fill="both", expand=True)

        # --- painel esquerdo (entradas) com rolagem
        esq_out = ttk.Frame(pan, width=390)
        canvas = tk.Canvas(esq_out, highlightthickness=0, width=380)
        sb = ttk.Scrollbar(esq_out, orient="vertical", command=canvas.yview)
        esq = ttk.Frame(canvas, padding=10)
        esq.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=esq, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        pan.add(esq_out, weight=0)

        # 1. arquivo
        g = ttk.LabelFrame(esq, text="1. Polígono", padding=8)
        g.pack(fill="x", pady=4)
        f = ttk.Frame(g); f.pack(fill="x")
        ttk.Entry(f, textvariable=self.v_arquivo).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="Procurar...", command=self.escolher_arquivo).pack(side="left", padx=(4, 0))
        ttk.Label(g, text="Polígono do arquivo:").pack(anchor="w", pady=(6, 0))
        self.cb_poly = ttk.Combobox(g, textvariable=self.v_poligono, state="readonly",
                                    values=["Automático (maior área)"])
        self.cb_poly.pack(fill="x")
        f = ttk.Frame(g); f.pack(fill="x", pady=(6, 0))
        ttk.Label(f, text="Área declarada (m², opcional):").pack(side="left")
        ttk.Entry(f, textvariable=self.v_area_decl, width=12).pack(side="right")

        # 2. hipotese de area
        g = ttk.LabelFrame(esq, text="2. O que o polígono representa?", padding=8)
        g.pack(fill="x", pady=4)
        ttk.Radiobutton(g, text="Projeção do EDIFÍCIO (item 4.1.1.2)",
                        variable=self.v_tipo, value="edificio").pack(anchor="w")
        ttk.Radiobutton(g, text="Terreno sem implantação definida (item 4.1.1.3)",
                        variable=self.v_tipo, value="terreno").pack(anchor="w")
        ttk.Radiobutton(g, text="Não sei - calcular as DUAS hipóteses",
                        variable=self.v_tipo, value="ambas").pack(anchor="w")
        ttk.Label(g, foreground="#a05000", wraplength=330, justify="left",
                  text="A regra de 1 furo/200 m² vale para a projeção do edifício, "
                       "não para o lote inteiro.").pack(anchor="w", pady=(4, 0))

        # 3. carga / profundidade
        g = ttk.LabelFrame(esq, text="3. Carga e profundidade", padding=8)
        g.pack(fill="x", pady=4)
        for txt, val in (("Nº de pavimentos", "pavimentos"),
                         ("Pressão média q (kPa)", "q"),
                         ("Sem carga (profundidade a definir)", "nenhuma")):
            ttk.Radiobutton(g, text=txt, variable=self.v_carga, value=val,
                            command=self._alterna_carga).pack(anchor="w")
        grid = ttk.Frame(g); grid.pack(fill="x", pady=4)
        self.e_pav = self._campo(grid, 0, "Pavimentos:", self.v_pav)
        self.e_qpav = self._campo(grid, 1, "kPa por pavimento:", self.v_qpav)
        self.e_q = self._campo(grid, 2, "q (kPa):", self.v_q)
        self._campo(grid, 3, "γ solo (kN/m³):", self.v_gama)
        ttk.Checkbutton(g, text="γ informado pelo projetista (não é estimativa)",
                        variable=self.v_gama_inf).pack(anchor="w")
        grid = ttk.Frame(g); grid.pack(fill="x", pady=(4, 0))
        self._campo(grid, 0, "Prof. mínima (m):", self.v_profmin)
        ttk.Label(grid, text="Fundação:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(grid, textvariable=self.v_fund, state="readonly", width=14,
                     values=["não definida", "rasa", "profunda"]).grid(row=1, column=1, sticky="e")
        grid.columnconfigure(1, weight=1)

        # 4. avancado
        g = ttk.LabelFrame(esq, text="4. Locação (avançado)", padding=8)
        g.pack(fill="x", pady=4)
        grid = ttk.Frame(g); grid.pack(fill="x")
        self._campo(grid, 0, "Forçar nº de furos:", self.v_n)
        ttk.Label(grid, text="Modo:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Combobox(grid, textvariable=self.v_modo, state="readonly", width=14,
                     values=["auto", "cantos", "malha"]).grid(row=1, column=1, sticky="e")
        self._campo(grid, 2, "Recuo da divisa (m):", self.v_recuo)
        self._campo(grid, 3, "Prefixo:", self.v_prefixo)
        self._campo(grid, 4, "Separador:", self.v_sep)
        self._campo(grid, 5, "Dígitos:", self.v_dig)
        grid.columnconfigure(1, weight=1)

        # 5. saida
        g = ttk.LabelFrame(esq, text="5. Pasta de saída", padding=8)
        g.pack(fill="x", pady=4)
        f = ttk.Frame(g); f.pack(fill="x")
        ttk.Entry(f, textvariable=self.v_saida).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="...", width=3, command=self.escolher_saida).pack(side="left", padx=(4, 0))

        self.bt_calc = ttk.Button(esq, text="▶  GERAR MAPA DE FUROS", style="Grande.TButton",
                                  command=self.calcular)
        self.bt_calc.pack(fill="x", pady=(10, 4), ipady=6)
        ttk.Button(esq, text="Abrir pasta de saída", command=self.abrir_saida).pack(fill="x")
        f = ttk.Frame(esq); f.pack(fill="x", pady=4)
        ttk.Button(f, text="Abrir KML (Google Earth)",
                   command=lambda: self.abrir_gerado("kml")).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="Abrir DXF",
                   command=lambda: self.abrir_gerado("dxf")).pack(side="left", fill="x", expand=True)

        # --- painel direito (resultados)
        dir_ = ttk.Frame(pan, padding=(4, 8, 8, 4))
        pan.add(dir_, weight=1)
        self.nb = ttk.Notebook(dir_)
        self.nb.pack(fill="both", expand=True)

        self.tab_res = ttk.Frame(self.nb)
        self.txt = tk.Text(self.tab_res, wrap="none", font=("Consolas", 10))
        ys = ttk.Scrollbar(self.tab_res, command=self.txt.yview)
        xs = ttk.Scrollbar(self.tab_res, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y"); xs.pack(side="bottom", fill="x")
        self.txt.pack(fill="both", expand=True)
        self.nb.add(self.tab_res, text="Resumo")

        self.tab_furos = ttk.Frame(self.nb)
        cols = ("hip", "id", "lat", "lon", "e", "n", "prof")
        self.tree = ttk.Treeview(self.tab_furos, columns=cols, show="headings")
        for c, t, w in zip(cols, ("Hipótese", "Furo", "Latitude", "Longitude",
                                  "E (m)", "N (m)", "Prof. (m)"),
                           (90, 90, 120, 120, 120, 130, 90)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        ys2 = ttk.Scrollbar(self.tab_furos, command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys2.set)
        ys2.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.nb.add(self.tab_furos, text="Furos")

        self.tab_planta = ttk.Frame(self.nb)
        top = ttk.Frame(self.tab_planta); top.pack(fill="x")
        ttk.Label(top, text="Hipótese:").pack(side="left", padx=4, pady=4)
        self.cb_planta = ttk.Combobox(top, state="readonly", width=14)
        self.cb_planta.pack(side="left")
        self.cb_planta.bind("<<ComboboxSelected>>", lambda e: self.mostrar_planta())
        ttk.Button(top, text="Abrir PNG", command=lambda: self.abrir_gerado("planta")).pack(side="left", padx=6)
        self.lb_img = ttk.Label(self.tab_planta, anchor="center")
        self.lb_img.pack(fill="both", expand=True)
        self.lb_img.bind("<Configure>", lambda e: self.mostrar_planta())
        self.nb.add(self.tab_planta, text="Planta")

        self.tab_norma = ttk.Frame(self.nb)
        tn = tk.Text(self.tab_norma, wrap="word", font=("Segoe UI", 10), padx=10, pady=10)
        ys3 = ttk.Scrollbar(self.tab_norma, command=tn.yview)
        tn.configure(yscrollcommand=ys3.set)
        ys3.pack(side="right", fill="y")
        tn.pack(fill="both", expand=True)
        for nome in ("nbr8036_regras.md", "profundidade.md"):
            try:
                with open(recurso("references", nome), encoding="utf-8") as fh:
                    tn.insert("end", fh.read() + "\n\n" + "-" * 80 + "\n\n")
            except OSError:
                pass
        tn.configure(state="disabled")
        self.nb.add(self.tab_norma, text="Norma")

        ttk.Label(self, textvariable=self.v_status, relief="sunken",
                  anchor="w", padding=(6, 2)).pack(fill="x", side="bottom")

        self.txt.insert("end", "Mapa de Furos - programação de sondagens SPT (NBR 8036:1983)\n\n"
                               "1) Abra o KML/KMZ (Google Earth) ou CSV de vértices.\n"
                               "2) Diga se o polígono é o EDIFÍCIO ou o TERRENO.\n"
                               "3) Informe pavimentos ou q para calcular a profundidade.\n"
                               "4) Clique em GERAR MAPA DE FUROS.\n\n"
                               "Saídas: KML, DXF (UTM), CSV, planta PNG, JSON e relatório TXT.\n")

    def _campo(self, pai, linha, rotulo, var):
        ttk.Label(pai, text=rotulo).grid(row=linha, column=0, sticky="w", pady=2)
        e = ttk.Entry(pai, textvariable=var, width=12)
        e.grid(row=linha, column=1, sticky="e", pady=2)
        pai.columnconfigure(1, weight=1)
        return e

    def _alterna_carga(self):
        c = self.v_carga.get()
        self.e_pav.configure(state="normal" if c == "pavimentos" else "disabled")
        self.e_qpav.configure(state="normal" if c == "pavimentos" else "disabled")
        self.e_q.configure(state="normal" if c == "q" else "disabled")

    # ------------------------------------------------------------ ações
    def escolher_arquivo(self):
        p = filedialog.askopenfilename(
            title="Selecione o polígono",
            filetypes=[("Polígonos", "*.kml *.kmz *.csv"), ("Todos", "*.*")])
        if not p:
            return
        self.v_arquivo.set(p)
        self.carregar_poligonos()

    def carregar_poligonos(self):
        p = self.v_arquivo.get()
        vals = ["Automático (maior área)"]
        self.poligonos = []
        if p.lower().endswith((".kml", ".kmz")):
            try:
                self.poligonos = core.listar_poligonos(p)
                vals += [f"[{i}] {n} - {br(a)} m²" for i, n, a in self.poligonos]
                self.v_status.set(f"{len(self.poligonos)} polígono(s) encontrado(s) em "
                                  f"{os.path.basename(p)}.")
            except Exception as e:
                messagebox.showerror(APP_NOME, f"Erro ao ler o arquivo:\n{e}")
        else:
            self.v_status.set("CSV de vértices carregado.")
        self.cb_poly.configure(values=vals)
        self.v_poligono.set(vals[0])

    def escolher_saida(self):
        p = filedialog.askdirectory(title="Pasta de saída", initialdir=self.v_saida.get())
        if p:
            self.v_saida.set(p)

    def abrir_saida(self):
        p = self.v_saida.get()
        os.makedirs(p, exist_ok=True)
        abrir_no_sistema(p)

    def abrir_gerado(self, chave):
        if not self.resultados:
            messagebox.showinfo(APP_NOME, "Gere o mapa de furos primeiro.")
            return
        res = self._res_selecionado()
        abrir_no_sistema(res["arquivos"][chave])

    def sobre(self):
        messagebox.showinfo(
            APP_NOME,
            f"{APP_NOME} v{APP_VERSAO}\n\n"
            "Programação de sondagens de simples reconhecimento (SPT)\n"
            "conforme ABNT NBR 8036:1983.\n\n"
            "Número, locação e profundidade prevista a partir de KML/KMZ/CSV.\n"
            "Os resultados são subsídio técnico e devem ser validados\n"
            "pelo engenheiro responsável.")

    # ----------------------------------------------------------- cálculo
    def _montar_args(self):
        arq = self.v_arquivo.get().strip()
        if not arq or not os.path.isfile(arq):
            raise ValueError("Selecione um arquivo KML, KMZ ou CSV válido.")
        saida = self.v_saida.get().strip() or pasta_padrao()
        base = [arq]
        ctx = {}

        sel = self.v_poligono.get()
        if sel.startswith("["):
            base += ["--indice", sel[1:sel.index("]")]]

        c = self.v_carga.get()
        if c == "pavimentos":
            pav = num(self.v_pav.get(), "o nº de pavimentos", obrigatorio=True)
            qpav = num(self.v_qpav.get(), "kPa por pavimento", obrigatorio=True)
            base += ["--pavimentos", str(pav), "--q-pav", str(qpav)]
            ctx["origem_q"] = (f"(ESTIMADO: {br(pav, 0)} pav × {br(qpav, 1)} kPa/pav)")
        elif c == "q":
            q = num(self.v_q.get(), "q", obrigatorio=True)
            base += ["--q", str(q)]
            ctx["origem_q"] = "(informado)"
        gama = num(self.v_gama.get(), "γ", obrigatorio=True)
        base += ["--gama", str(gama)]
        ctx["origem_gama"] = "(informado)" if self.v_gama_inf.get() else "(ESTIMADO - valor típico)"

        pm = num(self.v_profmin.get(), "profundidade mínima")
        if pm:
            base += ["--prof-min", str(pm)]
        n = num(self.v_n.get(), "nº de furos", inteiro=True)
        if n:
            base += ["--n", str(n)]
            ctx["n_forcado"] = True
        base += ["--modo", self.v_modo.get()]
        rec = (self.v_recuo.get() or "0").replace(",", ".")
        try:
            float(rec)
        except ValueError:
            raise ValueError("Recuo inválido.")
        base += ["--recuo", rec]
        base += ["--prefixo", self.v_prefixo.get() or "SPT",
                 "--separador", self.v_sep.get(),
                 "--digitos", str(num(self.v_dig.get(), "dígitos", inteiro=True) or 2)]
        ad = num(self.v_area_decl.get(), "área declarada")
        if ad:
            ctx["area_declarada"] = ad
        f = self.v_fund.get()
        ctx["fundacao"] = f if f in ("rasa", "profunda") else None

        tipos = ["edificio", "terreno"] if self.v_tipo.get() == "ambas" else [self.v_tipo.get()]
        execucoes = []
        for t in tipos:
            pasta = os.path.join(saida, t) if len(tipos) > 1 else saida
            execucoes.append((t, base + ["--tipo", t, "--saida", pasta]))
        return execucoes, ctx

    def calcular(self):
        try:
            execucoes, ctx = self._montar_args()
        except ValueError as e:
            messagebox.showwarning(APP_NOME, str(e))
            return
        self.bt_calc.configure(state="disabled")
        self.v_status.set("Calculando...")
        self.config(cursor="watch")

        def trabalho():
            try:
                saidas = []
                for t, argv in execucoes:
                    res = core.main(argv, imprimir=False)
                    texto = montar_relatorio(res, ctx)
                    rel = os.path.join(os.path.dirname(res["arquivos"]["kml"]),
                                       "sondagens_relatorio.txt")
                    with open(rel, "w", encoding="utf-8-sig") as fh:
                        fh.write(texto)
                    res["arquivos"]["relatorio"] = rel
                    texto = montar_relatorio(res, ctx)
                    saidas.append((res, texto))
                self.after(0, self._concluir, saidas, None)
            except SystemExit:
                self.after(0, self._concluir, None, "Parâmetros inválidos.")
            except Exception:
                self.after(0, self._concluir, None, traceback.format_exc())

        threading.Thread(target=trabalho, daemon=True).start()

    def _concluir(self, saidas, erro):
        self.bt_calc.configure(state="normal")
        self.config(cursor="")
        if erro:
            self.v_status.set("Erro no cálculo.")
            messagebox.showerror(APP_NOME, f"Erro no cálculo:\n\n{erro[-1500:]}")
            return
        self.resultados = saidas
        self.txt.delete("1.0", "end")
        if len(saidas) > 1:
            a, b = saidas[0][0], saidas[1][0]
            self.txt.insert("end",
                            "COMPARATIVO DAS HIPÓTESES\n"
                            f"  Edifício (4.1.1.2): {a['n_final']} furos\n"
                            f"  Terreno  (4.1.1.3): {b['n_final']} furos\n"
                            "  Confirme qual hipótese se aplica antes de contratar.\n\n")
        for _, texto in saidas:
            self.txt.insert("end", texto + "\n")

        self.tree.delete(*self.tree.get_children())
        for res, _ in saidas:
            for s in res["sondagens"]:
                self.tree.insert("", "end", values=(
                    res["tipo_area"], s["id"], f"{s['lat']:.7f}", f"{s['lon']:.7f}",
                    br(s["E"], 3), br(s["N"], 3), str(s["prof"]).replace(".", ",")))

        nomes = [r["tipo_area"] for r, _ in saidas]
        self.cb_planta.configure(values=nomes)
        self.cb_planta.set(nomes[0])
        self.mostrar_planta()
        r0 = saidas[0][0]
        self.v_status.set(f"Concluído: {' / '.join(str(r['n_final']) for r, _ in saidas)} "
                          f"furo(s). Arquivos em {os.path.dirname(r0['arquivos']['kml'])}")

    def _res_selecionado(self):
        nome = self.cb_planta.get()
        for r, _ in self.resultados:
            if r["tipo_area"] == nome:
                return r
        return self.resultados[0][0]

    def mostrar_planta(self):
        if not self.resultados:
            return
        try:
            from PIL import Image, ImageTk
            caminho = self._res_selecionado()["arquivos"]["planta"]
            img = Image.open(caminho)
            w = max(self.lb_img.winfo_width() - 10, 200)
            h = max(self.lb_img.winfo_height() - 10, 200)
            img.thumbnail((w, h), Image.LANCZOS)
            self._img_ref = ImageTk.PhotoImage(img)
            self.lb_img.configure(image=self._img_ref)
        except Exception as e:
            self.lb_img.configure(text=f"Não foi possível exibir a planta: {e}", image="")


def principal():
    # modo linha de comando: MapaDeFuros.exe arquivo.kml --tipo edificio ...
    args = sys.argv[1:]
    abrir = None
    if len(args) == 1 and args[0].lower().endswith((".kml", ".kmz", ".csv")) \
            and os.path.isfile(args[0]):
        abrir = args[0]          # "Abrir com..." / arrastar arquivo sobre o ícone
    elif args and args[0] != "--gui":
        core.main(imprimir=sys.stdout is not None)
        return
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = App()
    if abrir:
        app.v_arquivo.set(abrir)
        app.after(200, app.carregar_poligonos)
    app.mainloop()


if __name__ == "__main__":
    principal()
