# Mapa de Furos — Sondagens SPT (ABNT NBR 8036:1983)

Programa para Windows que converte um polígono (KML/KMZ do Google Earth ou CSV de
vértices) em um **plano de sondagens**: número de furos, locação, profundidade
prevista e as peças de saída.

## Uso
1. Abra o KML/KMZ/CSV (ou clique com o botão direito no arquivo › *Abrir com › Mapa de Furos*).
2. Escolha o polígono (se houver vários) e informe **o que ele representa**:
   projeção do **edifício** (4.1.1.2), **terreno** sem implantação (4.1.1.3) ou as duas hipóteses.
3. Informe nº de pavimentos ou a pressão média *q* e o peso específico γ.
4. Clique em **GERAR MAPA DE FUROS**.

Saídas (pasta escolhida, padrão `Documentos\MapaDeFuros`):

| Arquivo | Conteúdo |
|---|---|
| `sondagens.kml` | polígono + furos `SPT - 01`, `SPT - 02`… (Google Earth) |
| `sondagens.dxf` | polígono + furos em UTM (CAD) |
| `sondagens.csv` | lat/long, E/N, zona, profundidade (Excel, separador `;`) |
| `sondagens_planta.png` | planta de locação |
| `sondagens_resumo.json` | todos os números |
| `sondagens_relatorio.txt` | relatório com justificativa item a item |

## Linha de comando
O mesmo executável aceita os parâmetros do script original:

    MapaDeFuros.exe area.kml --tipo edificio --pavimentos 10 --saida C:\obra\sondagens

## Compilar o instalador
**Opção A – no seu PC Windows:** instale Python 3.12 (python.org) e Inno Setup 6
(jrsoftware.org) e dê dois cliques em `build_windows.bat`. Resultado:
`dist_instalador\MapaDeFuros_Setup_1.0.0.exe`.

**Opção B – na nuvem, sem instalar nada:** suba esta pasta para um repositório
GitHub, vá em *Actions › Build instalador Windows › Run workflow* e baixe o
artefato `MapaDeFuros-Windows` (instalador + versão portátil).

## Aviso
Os mínimos da norma são piso. q e γ não informados são **estimativas** e estão
marcados como tal no relatório. O resultado é subsídio técnico e deve ser
validado pelo engenheiro responsável.
