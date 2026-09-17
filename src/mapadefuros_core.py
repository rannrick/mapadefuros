#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Programacao de sondagens SPT conforme ABNT NBR 8036:1983.

Entrada : poligono em KML/KMZ (ou CSV de vertices lat,lon / E,N).
Saida   : numero de sondagens, locacao (KML, DXF, CSV, PNG) e profundidade
          estimada pelo criterio 4.1.2.2 (acrescimo de tensao < 10% da
          tensao geostatica efetiva), resolvido por Boussinesq/Newmark.

Sem dependencia de internet. Requer: numpy, scipy, matplotlib.

Uso tipico:
    python3 sondagens_nbr8036.py area.kml --tipo edificio --pavimentos 8 --saida ./out
    python3 sondagens_nbr8036.py gleba.kmz --tipo terreno --saida ./out
    python3 sondagens_nbr8036.py area.kml --tipo edificio --q 120 --gama 18 --n 9
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

import numpy as np

# ----------------------------------------------------------------------------
# 1. LEITURA DE KML / KMZ / CSV
# ----------------------------------------------------------------------------

def _strip_ns(tag):
    return tag.split('}')[-1] if '}' in tag else tag


def _parse_coord_text(txt):
    """'lon,lat,alt lon,lat,alt ...' -> [(lon, lat), ...]"""
    pts = []
    for tok in txt.replace('\n', ' ').replace('\t', ' ').split():
        parts = tok.split(',')
        if len(parts) >= 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    return pts


def listar_poligonos(caminho):
    """Lista (indice, nome, area_m2) dos poligonos de um KML/KMZ."""
    out = []
    for i, p in enumerate(ler_kml(caminho)):
        ll = np.array(p['outer'])
        pl = PlanoLocal(ll[:, 1].mean(), ll[:, 0].mean())
        a = area_gauss(pl.para_xy(ll)) - sum(
            area_gauss(pl.para_xy(h)) for h in p['holes'] if len(h) >= 3)
        out.append((i, p['nome'] or 'Poligono %d' % (i + 1), a))
    return out


def ler_kml(caminho):
    """Retorna lista de dicts: {'nome', 'outer': [(lon,lat)...], 'holes': [[...]]}"""
    if caminho.lower().endswith('.kmz'):
        with zipfile.ZipFile(caminho) as z:
            nome_kml = None
            for n in z.namelist():
                if n.lower().endswith('.kml'):
                    nome_kml = n
                    if os.path.basename(n).lower() == 'doc.kml':
                        break
            if nome_kml is None:
                raise ValueError('KMZ nao contem arquivo .kml')
            data = z.read(nome_kml)
    else:
        with open(caminho, 'rb') as f:
            data = f.read()

    root = ET.fromstring(data)
    poligonos = []

    def nome_do_placemark(el):
        for ch in el:
            if _strip_ns(ch.tag) == 'name' and ch.text:
                return ch.text.strip()
        return None

    def varrer(el, nome_pai=None):
        tag = _strip_ns(el.tag)
        nome = nome_do_placemark(el) or nome_pai if tag == 'Placemark' else nome_pai
        if tag == 'Polygon':
            outer, holes = [], []
            for sub in el.iter():
                st = _strip_ns(sub.tag)
                if st in ('outerBoundaryIs', 'innerBoundaryIs'):
                    for c in sub.iter():
                        if _strip_ns(c.tag) == 'coordinates' and c.text:
                            pts = _parse_coord_text(c.text)
                            if st == 'outerBoundaryIs':
                                outer = pts
                            else:
                                holes.append(pts)
            if outer:
                poligonos.append({'nome': nome or 'Poligono', 'outer': outer, 'holes': holes})
            return
        for ch in el:
            varrer(ch, nome)

    varrer(root)

    # fallback: LineString fechada (usuario desenhou "caminho" em vez de poligono)
    if not poligonos:
        for el in root.iter():
            if _strip_ns(el.tag) == 'LineString':
                for c in el.iter():
                    if _strip_ns(c.tag) == 'coordinates' and c.text:
                        pts = _parse_coord_text(c.text)
                        if len(pts) >= 4:
                            poligonos.append({'nome': 'LineString fechada',
                                              'outer': pts, 'holes': []})
    if not poligonos:
        raise ValueError('Nenhum poligono encontrado no arquivo.')
    return poligonos


def ler_csv_vertices(caminho):
    """CSV com colunas lat,lon (ou lon,lat / E,N com --zona). Retorna lista (lon,lat)."""
    pts = []
    with open(caminho, newline='', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            nums = []
            for c in row:
                c = c.strip().replace(',', '.') if c.count(',') == 1 and '.' not in c else c.strip()
                try:
                    nums.append(float(c))
                except ValueError:
                    pass
            if len(nums) >= 2:
                pts.append((nums[-1], nums[-2]) if abs(nums[-2]) <= 90 else (nums[-2], nums[-1]))
    return pts


# ----------------------------------------------------------------------------
# 2. GEODESIA: plano local (ENU) e UTM
# ----------------------------------------------------------------------------

A_WGS = 6378137.0
F_WGS = 1.0 / 298.257223563
E2 = F_WGS * (2 - F_WGS)


def raios(lat_rad):
    s = math.sin(lat_rad)
    w = math.sqrt(1 - E2 * s * s)
    N = A_WGS / w                      # grande normal
    M = A_WGS * (1 - E2) / (w ** 3)    # meridiana
    return M, N


class PlanoLocal:
    """Plano tangente local (metros reais no terreno) centrado no centroide."""

    def __init__(self, lat0, lon0):
        self.lat0, self.lon0 = lat0, lon0
        self.M, self.N = raios(math.radians(lat0))
        self.coslat = math.cos(math.radians(lat0))

    def para_xy(self, lonlat):
        arr = np.asarray(lonlat, dtype=float)
        x = np.radians(arr[:, 0] - self.lon0) * self.N * self.coslat
        y = np.radians(arr[:, 1] - self.lat0) * self.M
        return np.column_stack([x, y])

    def para_lonlat(self, xy):
        arr = np.asarray(xy, dtype=float)
        lon = self.lon0 + np.degrees(arr[:, 0] / (self.N * self.coslat))
        lat = self.lat0 + np.degrees(arr[:, 1] / self.M)
        return np.column_stack([lon, lat])


def latlon_para_utm(lat, lon, zona=None):
    k0 = 0.9996
    if zona is None:
        zona = int((lon + 180) / 6) + 1
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)
    phi, lam = math.radians(lat), math.radians(lon)
    ep2 = E2 / (1 - E2)
    Nn = A_WGS / math.sqrt(1 - E2 * math.sin(phi) ** 2)
    T = math.tan(phi) ** 2
    C = ep2 * math.cos(phi) ** 2
    Aa = math.cos(phi) * (lam - lon0)
    Mm = A_WGS * ((1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256) * phi
                  - (3 * E2 / 8 + 3 * E2 ** 2 / 32 + 45 * E2 ** 3 / 1024) * math.sin(2 * phi)
                  + (15 * E2 ** 2 / 256 + 45 * E2 ** 3 / 1024) * math.sin(4 * phi)
                  - (35 * E2 ** 3 / 3072) * math.sin(6 * phi))
    E = k0 * Nn * (Aa + (1 - T + C) * Aa ** 3 / 6
                   + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * Aa ** 5 / 120) + 500000.0
    Nrt = k0 * (Mm + Nn * math.tan(phi) * (Aa ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * Aa ** 4 / 24
                + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * Aa ** 6 / 720))
    if lat < 0:
        Nrt += 10000000.0
    return E, Nrt, zona, ('S' if lat < 0 else 'N')


# ----------------------------------------------------------------------------
# 3. GEOMETRIA PLANA
# ----------------------------------------------------------------------------

def area_gauss(xy):
    x, y = np.asarray(xy)[:, 0], np.asarray(xy)[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def perimetro(xy):
    d = np.diff(np.vstack([xy, xy[:1]]), axis=0)
    return float(np.sum(np.hypot(d[:, 0], d[:, 1])))


def dentro(pontos, outer, holes=()):
    """Ray casting vetorizado. pontos (n,2); outer/holes (m,2) sem repetir o 1o."""
    def _rc(P, poly):
        x, y = P[:, 0], P[:, 1]
        res = np.zeros(len(P), dtype=bool)
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            cond = ((y1 > y) != (y2 > y))
            with np.errstate(divide='ignore', invalid='ignore'):
                xint = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-300) + x1
            res ^= cond & (x < xint)
        return res
    ok = _rc(pontos, np.asarray(outer))
    for h in holes:
        ok &= ~_rc(pontos, np.asarray(h))
    return ok


def dist_segmentos(pontos, aneis):
    """Distancia minima de cada ponto ao contorno (todos os aneis)."""
    P = np.asarray(pontos, dtype=float)
    dmin = np.full(len(P), np.inf)
    for anel in aneis:
        Q = np.asarray(anel, dtype=float)
        A = Q
        B = np.roll(Q, -1, axis=0)
        AB = B - A
        L2 = np.sum(AB ** 2, axis=1)
        L2[L2 == 0] = 1e-12
        for i in range(len(A)):
            AP = P - A[i]
            t = np.clip((AP @ AB[i]) / L2[i], 0.0, 1.0)
            proj = A[i] + np.outer(t, AB[i])
            d = np.hypot(*(P - proj).T)
            dmin = np.minimum(dmin, d)
    return dmin


def retangulo_minimo(xy):
    """Retangulo de area minima circunscrito (rotating calipers).
    Retorna (B, L, angulo_rad, cantos(4,2))."""
    from scipy.spatial import ConvexHull
    P = np.asarray(xy, dtype=float)
    hull = P[ConvexHull(P).vertices]
    melhor = None
    n = len(hull)
    for i in range(n):
        e = hull[(i + 1) % n] - hull[i]
        ang = math.atan2(e[1], e[0])
        c, s = math.cos(-ang), math.sin(-ang)
        R = np.array([[c, -s], [s, c]])
        Q = hull @ R.T
        w = Q[:, 0].max() - Q[:, 0].min()
        h = Q[:, 1].max() - Q[:, 1].min()
        if melhor is None or w * h < melhor[0]:
            x0, x1 = Q[:, 0].min(), Q[:, 0].max()
            y0, y1 = Q[:, 1].min(), Q[:, 1].max()
            cantos = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]) @ np.linalg.inv(R).T
            melhor = (w * h, w, h, ang, cantos)
    _, w, h, ang, cantos = melhor
    B, L = (w, h) if w <= h else (h, w)
    return B, L, ang, cantos


# ----------------------------------------------------------------------------
# 4. NUMERO DE SONDAGENS - NBR 8036 item 4.1.1.2 / 4.1.1.3
# ----------------------------------------------------------------------------

def numero_sondagens(area_m2, tipo='edificio'):
    """tipo='edificio' -> area = projecao em planta do edificio (4.1.1.2)
       tipo='terreno'  -> sem disposicao em planta (4.1.1.3): min 3, malha <=100 m
    Retorna (n, criterio_texto, extrapolado_bool)"""
    extrap = False
    if tipo == 'terreno':
        return 3, ('4.1.1.3 - sem disposicao em planta dos edificios: minimo de 3 '
                   'sondagens e espacamento maximo de 100 m entre elas'), False
    A = float(area_m2)
    if A <= 200:
        n, crit = 2, '4.1.1.2-a - area ate 200 m2: minimo de 2 sondagens'
    elif A <= 400:
        n, crit = 3, '4.1.1.2-b - area entre 200 e 400 m2: minimo de 3 sondagens'
    elif A <= 1200:
        n = max(3, math.ceil(A / 200.0))
        crit = '4.1.1.2 - 1 sondagem a cada 200 m2 ate 1200 m2'
    elif A <= 2400:
        n = 6 + math.ceil((A - 1200) / 400.0)
        crit = ('4.1.1.2 - 6 sondagens (1200 m2 / 200 m2) + 1 a cada 400 m2 '
                'excedentes de 1200 m2')
    else:
        n = 6 + math.ceil((A - 1200) / 400.0)
        crit = ('4.1.1.2 - acima de 2400 m2 a norma remete ao PLANO PARTICULAR DA '
                'CONSTRUCAO. Adotada, como piso, a extrapolacao de 1 sondagem a cada '
                '400 m2 excedentes de 1200 m2 - confirmar com o projetista')
        extrap = True
    return int(n), crit, extrap


# ----------------------------------------------------------------------------
# 5. LOCACAO - itens 4.1.1.3 e 4.1.1.4
# ----------------------------------------------------------------------------

def malha_interna(outer, holes, passo_alvo=None):
    """Nuvem densa de pontos internos, usada para Lloyd e verificacao de cobertura."""
    P = np.asarray(outer)
    x0, y0 = P.min(axis=0)
    x1, y1 = P.max(axis=0)
    ar = area_gauss(P)
    passo = passo_alvo or max(0.4, math.sqrt(ar / 6000.0))
    gx = np.arange(x0, x1 + passo, passo)
    gy = np.arange(y0, y1 + passo, passo)
    GX, GY = np.meshgrid(gx, gy)
    cand = np.column_stack([GX.ravel(), GY.ravel()])
    return cand[dentro(cand, outer, holes)], passo


def lloyd(sementes, nuvem, iters=60, fixos=0):
    """Relaxacao de Lloyd (CVT) -> pontos igualmente distribuidos em toda a area.
    Os `fixos` primeiros pontos nao se movem (usado para ancorar os cantos)."""
    C = np.array(sementes, dtype=float)
    for _ in range(iters):
        d = ((nuvem[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        novo = C.copy()
        for k in range(fixos, len(C)):
            m = lab == k
            if m.any():
                novo[k] = nuvem[m].mean(axis=0)
        if np.allclose(novo, C, atol=1e-3):
            C = novo
            break
        C = novo
    return C


def sementes_em_malha(n, cantos, ang, nuvem):
    """Sementes iniciais em malha alinhada ao retangulo minimo (distribuicao regular)."""
    c, s = math.cos(-ang), math.sin(-ang)
    R = np.array([[c, -s], [s, c]])
    Q = nuvem @ R.T
    x0, x1 = Q[:, 0].min(), Q[:, 0].max()
    y0, y1 = Q[:, 1].min(), Q[:, 1].max()
    W, H = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    melhor = None
    for nx in range(1, n + 1):
        ny = math.ceil(n / nx)
        razao = (W / nx) / (H / ny)
        custo = abs(math.log(razao)) + 0.25 * abs(nx * ny - n)
        if melhor is None or custo < melhor[0]:
            melhor = (custo, nx, ny)
    _, nx, ny = melhor
    px = x0 + (np.arange(nx) + 0.5) * W / nx
    py = y0 + (np.arange(ny) + 0.5) * H / ny
    G = np.array([[a, b] for b in py for a in px])
    G = G @ np.linalg.inv(R).T
    # mantem os n mais proximos da nuvem valida
    d = ((G[:, None, :] - nuvem[None, :, :]) ** 2).sum(axis=2).min(axis=1)
    idx = np.argsort(d)[:n]
    G = G[idx]
    # puxa qualquer semente fora da area para o ponto interno mais proximo
    for i, g in enumerate(G):
        dd = ((nuvem - g) ** 2).sum(axis=1)
        G[i] = nuvem[dd.argmin()]
    return G


def corrigir_alinhamento(C, nuvem, tol=0.10):
    """4.1.1.4-b: com mais de 3 sondagens elas nao podem ficar em um mesmo alinhamento."""
    if len(C) <= 3:
        return C, False
    X = C - C.mean(axis=0)
    sv = np.linalg.svd(X, compute_uv=False)
    if sv[0] < 1e-9 or sv[1] / sv[0] > tol:
        return C, False
    u, _, vt = np.linalg.svd(X)
    normal = vt[1]
    desl = 0.25 * sv[0] / math.sqrt(len(C))
    C2 = C.copy()
    for i in range(len(C2)):
        C2[i] = C2[i] + normal * desl * (1 if i % 2 == 0 else -1)
        dd = ((nuvem - C2[i]) ** 2).sum(axis=1)
        C2[i] = nuvem[dd.argmin()]
    return C2, True


def ancorar_cantos(cantos, nuvem, recuo):
    """Pontos proximos aos vertices do retangulo circunscrito, recuados para dentro.
    Reproduz a pratica corrente de investigar as extremidades da area carregada."""
    centro = np.asarray(cantos).mean(axis=0)
    fixos = []
    for c in cantos:
        v = centro - c
        nv = np.linalg.norm(v)
        alvo = c + v / max(nv, 1e-9) * min(max(recuo * 1.5, 1.0), 0.35 * nv)
        dd = ((nuvem - alvo) ** 2).sum(axis=1)
        p = nuvem[dd.argmin()]
        if not any(np.allclose(p, f, atol=1e-6) for f in fixos):
            fixos.append(p)
    return np.array(fixos) if fixos else np.zeros((0, 2))


def locar(outer, holes, n, recuo=2.0, espacamento_max=None, max_n=200, modo='auto'):
    """Distribui n sondagens. Se espacamento_max for dado (4.1.1.3), aumenta n
    ate que nenhum ponto da area fique a mais de espacamento_max/2 de uma sondagem."""
    nuvem_full, passo = malha_interna(outer, holes)
    if len(nuvem_full) < 8:
        nuvem_full, passo = malha_interna(outer, holes, passo_alvo=passo / 4)
    aneis = [np.asarray(outer)] + [np.asarray(h) for h in holes]
    db = dist_segmentos(nuvem_full, aneis)
    rec = recuo
    while rec > 0.05 and (db >= rec).sum() < max(8, n * 3):
        rec /= 2.0
    nuvem = nuvem_full[db >= rec] if (db >= rec).sum() >= max(4, n) else nuvem_full

    B, L, ang, cantos = retangulo_minimo(np.asarray(outer))
    n_atual = n
    usa_cantos = (modo == 'cantos') or (modo == 'auto' and espacamento_max is None)
    while True:
        sem = sementes_em_malha(n_atual, cantos, ang, nuvem)
        nfix = 0
        if usa_cantos and n_atual >= 4:
            fix = ancorar_cantos(cantos, nuvem, rec)
            nfix = len(fix)
            if nfix and n_atual > nfix:
                # descarta as sementes mais proximas dos cantos ancorados
                d = ((sem[:, None, :] - fix[None, :, :]) ** 2).sum(axis=2).min(axis=1)
                sem = sem[np.argsort(d)[::-1][:n_atual - nfix]]
                sem = np.vstack([fix, sem])
            else:
                nfix = 0
        C = lloyd(sem, nuvem, fixos=nfix)
        for i in range(len(C)):
            dd = ((nuvem - C[i]) ** 2).sum(axis=1)
            C[i] = nuvem[dd.argmin()]
        C = np.unique(np.round(C, 3), axis=0)
        C, ajust = corrigir_alinhamento(C, nuvem)
        cobertura = float(np.max(np.sqrt(((nuvem_full[:, None, :] - C[None, :, :]) ** 2)
                                         .sum(axis=2)).min(axis=1)))
        if espacamento_max is None or cobertura <= espacamento_max / math.sqrt(2) \
                or n_atual >= max_n:
            break
        n_atual += 1
    C = ordenar_furos(C, ang)
    return C, cobertura, rec, ajust, n_atual


def ordenar_furos(C, ang):
    """Numeracao em varredura (esq->dir, de cima para baixo) no eixo do retangulo."""
    if len(C) < 2:
        return C
    c, s = math.cos(-ang), math.sin(-ang)
    R = np.array([[c, -s], [s, c]])
    Q = C @ R.T
    D = np.sqrt(((C[:, None, :] - C[None, :, :]) ** 2).sum(axis=2))
    np.fill_diagonal(D, np.inf)
    passo = max(float(np.median(D.min(axis=1))) * 0.7, 1e-6)
    faixa = np.round((Q[:, 1].max() - Q[:, 1]) / passo).astype(int)
    ordem = sorted(range(len(C)), key=lambda i: (faixa[i], Q[i, 0]))
    return C[ordem]


def estatisticas_espacamento(C):
    if len(C) < 2:
        return {'min': None, 'max_vizinho': None, 'medio': None}
    D = np.sqrt(((C[:, None, :] - C[None, :, :]) ** 2).sum(axis=2))
    np.fill_diagonal(D, np.inf)
    viz = D.min(axis=1)
    return {'min': float(viz.min()), 'max_vizinho': float(viz.max()),
            'medio': float(viz.mean())}


# ----------------------------------------------------------------------------
# 6. PROFUNDIDADE - itens 4.1.2.2 e 4.1.2.3 (grafico da Figura)
# ----------------------------------------------------------------------------

def fator_influencia_canto(m, n):
    """Newmark: acrescimo de tensao vertical sob o CANTO de retangulo carregado."""
    m2, n2 = m * m, n * n
    s = m2 + n2 + 1.0
    raiz = math.sqrt(s)
    t1 = (2 * m * n * raiz / (s + m2 * n2)) * ((s + 1.0) / s)
    den = s - m2 * n2
    ang = math.atan2(2 * m * n * raiz, den)
    if den < 0:
        ang = math.atan(2 * m * n * raiz / den) + math.pi
    return (t1 + ang) / (4 * math.pi)


def influencia_centro(D, B, L):
    """Acrescimo relativo de tensao no centro da area retangular B x L, na cota D."""
    if D <= 1e-9:
        return 1.0
    return 4.0 * fator_influencia_canto((B / 2.0) / D, (L / 2.0) / D)


def profundidade_criterio(q, gama, B, L, M=0.1):
    """Resolve q*I(D) = M*gama*D  (item 4.1.2.2). Retorna D em metros."""
    f = lambda D: q * influencia_centro(D, B, L) - M * gama * D
    lo, hi = 1e-3, max(50.0, 40.0 * B)
    if f(hi) > 0:
        return hi, False
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), True


def pressao_estimada(pavimentos, por_pavimento=12.0):
    """q medio (kPa) = peso do edificio / area em planta. Padrao 12 kPa/pavimento."""
    return float(pavimentos) * float(por_pavimento)


def nome_base_seguro(nome):
    """Sanitiza um nome (ex.: nome do poligono) para uso como base de nome de arquivo."""
    nome = re.sub(r'[\\/:*?"<>|]+', '_', (nome or '').strip())
    nome = nome.strip(' .')
    return nome or 'sondagens'


# ----------------------------------------------------------------------------
# 7. SAIDAS
# ----------------------------------------------------------------------------

def escrever_kml(caminho, lonlat_poly, holes_lonlat, pontos_lonlat, rotulos, descricoes,
                 nome='Programacao de sondagens - NBR 8036'):
    def coords(pts):
        return ' '.join('%.8f,%.8f,0' % (p[0], p[1]) for p in pts)

    ring = list(lonlat_poly)
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    inner = ''
    for h in holes_lonlat:
        hh = list(h)
        if hh[0] != hh[-1]:
            hh.append(hh[0])
        inner += ('<innerBoundaryIs><LinearRing><coordinates>%s</coordinates>'
                  '</LinearRing></innerBoundaryIs>' % coords(hh))

    marcas = []
    for (lon, lat), rot, desc in zip(pontos_lonlat, rotulos, descricoes):
        marcas.append(
            '<Placemark><name>%s</name><description><![CDATA[%s]]></description>'
            '<styleUrl>#sp</styleUrl>'
            '<Point><coordinates>%.8f,%.8f,0</coordinates></Point></Placemark>'
            % (rot, desc, lon, lat))

    kml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>%s</name>'
           '<Style id="sp"><IconStyle><color>ff0000ff</color><scale>1.1</scale>'
           '<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
           '</href></Icon></IconStyle><LabelStyle><scale>0.9</scale></LabelStyle></Style>'
           '<Style id="area"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle>'
           '<PolyStyle><color>3300ffff</color></PolyStyle></Style>'
           '<Placemark><name>Area de estudo</name><styleUrl>#area</styleUrl><Polygon>'
           '<outerBoundaryIs><LinearRing><coordinates>%s</coordinates></LinearRing>'
           '</outerBoundaryIs>%s</Polygon></Placemark>%s</Document></kml>'
           % (nome, coords(ring), inner, ''.join(marcas)))
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(kml)


def escrever_dxf(caminho, poly_en, holes_en, pontos_en, rotulos, raio=1.5, texto_h=2.0):
    """DXF R12 ASCII em coordenadas UTM (E, N)."""
    out = []
    add = out.append
    add('0\nSECTION\n2\nENTITIES')

    def polilinha(pts, layer):
        add('0\nPOLYLINE\n8\n%s\n66\n1\n70\n1' % layer)
        for p in pts:
            add('0\nVERTEX\n8\n%s\n10\n%.3f\n20\n%.3f' % (layer, p[0], p[1]))
        add('0\nSEQEND\n8\n%s' % layer)

    polilinha(poly_en, 'AREA')
    for h in holes_en:
        polilinha(h, 'AREA')
    for (e, n), rot in zip(pontos_en, rotulos):
        add('0\nCIRCLE\n8\nSONDAGENS\n10\n%.3f\n20\n%.3f\n40\n%.3f' % (e, n, raio))
        add('0\nPOINT\n8\nSONDAGENS\n10\n%.3f\n20\n%.3f' % (e, n))
        add('0\nTEXT\n8\nSONDAGENS_TXT\n10\n%.3f\n20\n%.3f\n40\n%.3f\n1\n%s'
            % (e + raio * 1.4, n + raio * 0.6, texto_h, rot))
    add('0\nENDSEC\n0\nEOF')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


def escrever_csv(caminho, linhas):
    with open(caminho, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['Sondagem', 'Latitude', 'Longitude', 'E (m)', 'N (m)',
                    'Zona UTM', 'Profundidade prevista (m)'])
        for l in linhas:
            w.writerow(l)


def desenhar_planta(caminho, poly_xy, holes_xy, C, rotulos, cantos, B, L, titulo):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 9))
    P = np.vstack([poly_xy, poly_xy[:1]])
    ax.plot(P[:, 0], P[:, 1], '-', color='#1f4e79', lw=2, label='Area de estudo')
    ax.fill(P[:, 0], P[:, 1], color='#1f4e79', alpha=0.06)
    for h in holes_xy:
        H = np.vstack([h, h[:1]])
        ax.plot(H[:, 0], H[:, 1], '--', color='#1f4e79', lw=1.2)
    R = np.vstack([cantos, cantos[:1]])
    ax.plot(R[:, 0], R[:, 1], ':', color='#888888', lw=1.2,
            label='Retangulo circunscrito (B=%.1f m, L=%.1f m)' % (B, L))
    ax.plot(C[:, 0], C[:, 1], 'o', color='#c00000', ms=8, label='Sondagens (%d)' % len(C))
    for (x, y), r in zip(C, rotulos):
        ax.annotate(r, (x, y), textcoords='offset points', xytext=(8, 6),
                    fontsize=9, color='#c00000', weight='bold')
    ax.set_aspect('equal')
    ax.grid(alpha=0.25, ls=':')
    ax.set_xlabel('Este local (m)')
    ax.set_ylabel('Norte local (m)')
    ax.set_title(titulo, fontsize=11)
    ax.margins(0.10)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=8,
              frameon=False)
    fig.tight_layout()
    fig.savefig(caminho, dpi=160)
    plt.close(fig)


# ----------------------------------------------------------------------------
# 8. MAIN
# ----------------------------------------------------------------------------

def main(argv=None, imprimir=True):
    ap = argparse.ArgumentParser(description='Programacao de sondagens - NBR 8036:1983')
    ap.add_argument('arquivo', help='KML, KMZ ou CSV de vertices')
    ap.add_argument('--tipo', choices=['edificio', 'terreno'], default='edificio',
                    help='edificio = poligono e a projecao em planta do edificio '
                         '(4.1.1.2); terreno = area sem disposicao em planta (4.1.1.3)')
    ap.add_argument('--indice', type=int, default=None,
                    help='indice do poligono no KML (default: o de maior area)')
    ap.add_argument('--n', type=int, default=None, help='forcar numero de sondagens')
    ap.add_argument('--q', type=float, default=None, help='pressao media q (kPa)')
    ap.add_argument('--pavimentos', type=float, default=None,
                    help='n de pavimentos (estima q = pav x --q-pav)')
    ap.add_argument('--q-pav', type=float, default=12.0, help='kPa por pavimento (12)')
    ap.add_argument('--gama', type=float, default=18.0, help='peso especifico (kN/m3)')
    ap.add_argument('--B', type=float, default=None, help='forcar B (m)')
    ap.add_argument('--L', type=float, default=None, help='forcar L (m)')
    ap.add_argument('--modo', choices=['auto','cantos','malha'], default='auto',
                    help='cantos = ancora furos nas extremidades da area carregada; '
                         'malha = distribuicao regular tipo CVT')
    ap.add_argument('--recuo', type=float, default=2.0,
                    help='afastamento minimo da divisa (m)')
    ap.add_argument('--prof-min', type=float, default=None,
                    help='profundidade minima a adotar (m)')
    ap.add_argument('--prefixo', default='SPT',
                    help='prefixo dos furos (padrao SPT -> "SPT - 01")')
    ap.add_argument('--separador', default=' - ',
                    help='separador entre prefixo e numero (padrao " - ")')
    ap.add_argument('--digitos', type=int, default=2,
                    help='digitos do numero sequencial (padrao 2 -> 01, 02, ...)')
    ap.add_argument('--nome-base', default='sondagens',
                    help='nome base dos arquivos gerados (padrao "sondagens")')
    ap.add_argument('--saida', default='./saida_sondagens')
    args = ap.parse_args(argv)

    os.makedirs(args.saida, exist_ok=True)

    # --- geometria de entrada
    if args.arquivo.lower().endswith(('.kml', '.kmz')):
        polys = ler_kml(args.arquivo)
        if args.indice is not None:
            poly = polys[args.indice]
        else:
            def ar(p):
                ll = np.array(p['outer'])
                pl = PlanoLocal(ll[:, 1].mean(), ll[:, 0].mean())
                return area_gauss(pl.para_xy(ll))
            poly = max(polys, key=ar)
        outer_ll, holes_ll = poly['outer'], poly['holes']
        nome_poly = poly['nome']
        n_polys = len(polys)
    else:
        outer_ll, holes_ll, nome_poly, n_polys = ler_csv_vertices(args.arquivo), [], 'CSV', 1

    outer_ll = [p for i, p in enumerate(outer_ll)
                if i == 0 or p != outer_ll[i - 1]]
    if len(outer_ll) > 1 and outer_ll[0] == outer_ll[-1]:
        outer_ll = outer_ll[:-1]
    holes_ll = [h[:-1] if len(h) > 1 and h[0] == h[-1] else h for h in holes_ll]

    arr = np.array(outer_ll)
    lat0, lon0 = float(arr[:, 1].mean()), float(arr[:, 0].mean())
    plano = PlanoLocal(lat0, lon0)
    outer = plano.para_xy(outer_ll)
    holes = [plano.para_xy(h) for h in holes_ll]

    area = area_gauss(outer) - sum(area_gauss(h) for h in holes)
    perim = perimetro(outer)
    B_mbr, L_mbr, ang, cantos = retangulo_minimo(outer)
    B = args.B or B_mbr
    L = args.L or L_mbr

    # --- numero de sondagens
    n_norma, criterio, extrap = numero_sondagens(area, args.tipo)
    n_alvo = args.n or n_norma
    esp_max = 100.0 if args.tipo == 'terreno' else None

    C, cobertura, recuo_usado, ajustou_alinhamento, n_final = locar(
        outer, holes, n_alvo, recuo=args.recuo, espacamento_max=esp_max, modo=args.modo)
    nd = max(args.digitos, len(str(len(C))))
    rotulos = ['%s%s%s' % (args.prefixo, args.separador, str(i + 1).zfill(nd))
               for i in range(len(C))]
    esp = estatisticas_espacamento(C)

    # --- profundidade
    q = args.q if args.q is not None else (
        pressao_estimada(args.pavimentos, args.q_pav) if args.pavimentos else None)
    prof = None
    convergiu = None
    if q:
        prof, convergiu = profundidade_criterio(q, args.gama, B, L)
    prof_adot = max(prof or 0, args.prof_min or 0) or None

    # --- coordenadas de saida
    C_ll = plano.para_lonlat(C)
    zona_ref = None
    linhas, descr = [], []
    pontos_en = []
    for i, (lon, lat) in enumerate(C_ll):
        E, N, z, hemi = latlon_para_utm(lat, lon, zona_ref)
        zona_ref = z
        pontos_en.append((E, N))
        pz = ('%.2f' % prof_adot) if prof_adot else 'a definir'
        linhas.append([rotulos[i], '%.8f' % lat, '%.8f' % lon, '%.3f' % E, '%.3f' % N,
                       '%d%s' % (z, hemi), pz])
        descr.append('Lat %.6f / Lon %.6f<br/>UTM %d%s E %.2f N %.2f<br/>'
                     'Profundidade prevista: %s m' % (lat, lon, z, hemi, E, N, pz))

    poly_en = [latlon_para_utm(p[1], p[0], zona_ref)[:2] for p in outer_ll]
    holes_en = [[latlon_para_utm(p[1], p[0], zona_ref)[:2] for p in h] for h in holes_ll]

    base = os.path.join(args.saida, nome_base_seguro(args.nome_base))
    escrever_kml(base + '.kml', outer_ll, holes_ll, C_ll, rotulos, descr)
    escrever_dxf(base + '.dxf', poly_en, holes_en, pontos_en, rotulos)
    escrever_csv(base + '.csv', linhas)
    desenhar_planta(base + '_planta.png', outer, holes, C, rotulos, cantos, B, L,
                    'Locacao das sondagens - NBR 8036 (%d furos / %.0f m2)'
                    % (len(C), area))

    res = {
        'arquivo': os.path.basename(args.arquivo),
        'poligono': nome_poly,
        'poligonos_no_arquivo': n_polys,
        'tipo_area': args.tipo,
        'area_m2': round(area, 2),
        'area_ha': round(area / 10000.0, 4),
        'perimetro_m': round(perim, 2),
        'vertices': len(outer_ll),
        'B_m': round(B, 2), 'L_m': round(L, 2), 'L_sobre_B': round(L / B, 2),
        'utm_zona': '%d%s' % (zona_ref, 'S' if lat0 < 0 else 'N'),
        'centroide': {'lat': round(lat0, 8), 'lon': round(lon0, 8)},
        'n_norma': n_norma,
        'n_final': len(C),
        'criterio_numero': criterio,
        'acima_2400_extrapolado': extrap,
        'espacamento_m': {k: (round(v, 2) if v else v) for k, v in esp.items()},
        'dist_max_area_ate_furo_m': round(cobertura, 2),
        'recuo_divisa_m': round(recuo_usado, 2),
        'corrigiu_alinhamento': bool(ajustou_alinhamento),
        'check_4_1_1_4_b': ('OK - nao alinhadas' if len(C) <= 3 else 'OK - nao colineares'),
        'check_4_1_1_3_100m': (None if esp_max is None else
                               ('OK' if (esp['max_vizinho'] or 0) <= 100 and cobertura <= 70.7
                                else 'VERIFICAR')),
        'profundidade': {
            'q_kPa': q, 'gama_kNm3': args.gama, 'M': 0.1,
            'q_sobre_gama_M_B': (round(q / (args.gama * 0.1 * B), 3) if q else None),
            'D_criterio_m': (round(prof, 2) if prof else None),
            'D_sobre_B': (round(prof / B, 3) if prof else None),
            'D_adotada_m': (round(prof_adot, 2) if prof_adot else None),
            'convergiu': convergiu,
        },
        'arquivos': {
            'kml': base + '.kml', 'dxf': base + '.dxf',
            'csv': base + '.csv', 'planta': base + '_planta.png',
        },
        'sondagens': [
            {'id': l[0], 'lat': float(l[1]), 'lon': float(l[2]),
             'E': float(l[3]), 'N': float(l[4]), 'prof': l[6]} for l in linhas
        ],
    }
    with open(base + '_resumo.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    res['arquivos']['json'] = base + '_resumo.json'
    if imprimir:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


if __name__ == '__main__':
    main()
