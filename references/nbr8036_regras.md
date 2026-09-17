# NBR 8036:1983 — regras aplicáveis, tabela de decisão e checklist

Norma: *Programação de sondagens de simples reconhecimento dos solos para fundações
de edifícios* (ABNT, jun/1983, origem NB-12/1979). Fixa **número, localização e
profundidade**. A execução do furo é objeto de outra norma; terminologia na NBR 6502
(item 2/3).

---

## 1. Número de sondagens

### 1.1 Item 4.1.1.1 — princípio

O número e a localização dependem do **tipo de estrutura**, de suas características
especiais e das condições geotécnicas do subsolo, e devem ser suficientes para dar o
melhor quadro possível da provável variação das camadas. Ou seja: os mínimos abaixo
são piso, não teto. Recomende acréscimo quando houver aterro, solo mole, encosta,
subsolo reconhecidamente errático, obra de grande porte ou fundação profunda.

### 1.2 Item 4.1.1.2 — projeção em planta do EDIFÍCIO

| Área A da projeção | Número |
|---|---|
| A ≤ 200 m² | **2** (mínimo da alínea *a*) |
| 200 < A ≤ 400 m² | **3** (mínimo da alínea *b*) |
| 400 < A ≤ 1.200 m² | 1 a cada 200 m² → `teto(A/200)`, nunca menos que 3 |
| 1.200 < A ≤ 2.400 m² | 6 + 1 a cada 400 m² excedentes de 1.200 → `6 + teto((A−1200)/400)` |
| A > 2.400 m² | **fixado conforme o plano particular da construção** |

Sobre A > 2.400 m²: a norma não dá fórmula. O script continua a progressão de
1/400 m² apenas como **piso adotado**, e marca `acima_2400_extrapolado: true`.
Ao redigir, deixe explícito que é critério adotado e que o projetista deve
confirmá-lo em função da estrutura (juntas de dilatação, blocos, torres, áreas
de carga concentrada).

Exemplos de conferência:
- 180 m² → 2 · 350 m² → 3 · 900 m² → 5 · 1.200 m² → 6 · 1.202,56 m² → 7 · 2.400 m² → 9

### 1.3 Item 4.1.1.3 — sem disposição em planta

Viabilidade ou escolha de local: espaçamento máximo de **100 m** entre sondagens,
**mínimo de 3**. É este o caso de "me diz quantos furos nesse terreno" sem projeto.
O script (`--tipo terreno`) aumenta o número até que nenhum ponto da área fique a
mais de 100/√2 ≈ 70,7 m de um furo — equivalente a uma malha de 100 m.

### 1.4 Item 4.1.2.4 — vários corpos

Planta composta de vários corpos: o critério **se aplica a cada corpo**. Rode um
cálculo por bloco e some, em vez de tratar o conjunto como uma área única.

---

## 2. Localização — item 4.1.1.4

- **a)** Fase preliminar/planejamento: furos **igualmente distribuídos em toda a
  área**. Na fase de projeto, pode-se locar por critério específico que considere
  pormenores estruturais (pilares mais carregados, poços, juntas, blocos isolados).
- **b)** Com **mais de três** sondagens, elas **não podem** ficar ao longo de um
  mesmo alinhamento — é preciso haver espalhamento em duas direções para
  caracterizar mergulho e variação lateral das camadas.

O script atende (a) por relaxação de Lloyd/CVT (distribuição igual mesmo em áreas
irregulares, em L, com furos internos) e verifica (b) por decomposição em valores
singulares, corrigindo automaticamente se os pontos saírem colineares.

Ajustes de campo que a norma não trata mas o plano deve prever: afastamento de
divisas, taludes, redes enterradas e árvores; acesso do equipamento; e realocação
com registro em ART quando o ponto projetado for inviável.

---

## 3. Profundidade

### 3.1 Item 4.1.2.1 — princípio
Função do tipo de edifício, das características da estrutura, das dimensões em
planta, da forma da área carregada e das condições geotécnicas e topográficas.
**Nota da norma:** a exploração deve alcançar todas as camadas impróprias ou
questionáveis como apoio, de modo a não comprometer estabilidade nem comportamento
estrutural/funcional.

### 3.2 Item 4.1.2.2 — critério dos 10%
Levar até onde o **acréscimo de pressão** devido às cargas estruturais seja **menor
que 10% da pressão geostática efetiva**. Ver `profundidade.md` para a solução.

### 3.3 Item 4.1.2.3 — gráfico da Figura
Guia de estimativa: `q/(γ·M·B)` × `D/B`, curvas por `L/B` (1, 2, 3, 5, 8, 15, ∞),
com M = 0,1; B e L do retângulo circunscrito à planta; D a profundidade.

### 3.4 Itens 4.1.2.5 a 4.1.2.10 — ajustes e paradas

| Item | Regra |
|---|---|
| 4.1.2.5 | Corpos de fundação isolados e muito espaçados: considerar simultaneamente a **menor dimensão do corpo**, a profundidade dos elementos e a pressão transmitida |
| 4.1.2.6 | Pode-se **parar** ao atingir camada de compacidade/consistência elevada, se a geologia local mostrar não haver camada menos resistente abaixo |
| 4.1.2.7 | Pode-se parar em **rocha ou camada impenetrável à percussão** sobrejacente a solo adequado. Em fundações de importância, ou se as camadas superiores não servirem de suporte, verificar natureza e continuidade da camada — **mínimo de 5 m** de investigação |
| 4.1.2.8 | Contar a profundidade **da superfície do terreno**, sem descontar a camada a ser escavada |
| 4.1.2.9 | Fundação profunda (estacas/tubulões): contar a partir da **provável ponta da estaca ou base do tubulão** — a profundidade total do furo é essa cota mais o D calculado |
| 4.1.2.10 | Considerações especiais onde houver processos de alteração posteriores: erosão, expansão e outros |

---

## 4. Checklist de conformidade (rodar antes de entregar)

1. A área usada é a **projeção do edifício** (4.1.1.2) ou o caso sem planta
   (4.1.1.3)? Está dito explicitamente na resposta?
2. O número respeita os mínimos (2 / 3 / 3)?
3. Se A > 2.400 m², está sinalizado que o número depende do plano particular da
   construção?
4. Vários corpos → o critério foi aplicado **a cada corpo** (4.1.2.4)?
5. Os furos estão distribuídos em toda a área (4.1.1.4-a)?
6. Com mais de 3 furos, eles **não** estão em um mesmo alinhamento (4.1.1.4-b)?
7. No caso 4.1.1.3, algum par de furos vizinhos ultrapassa 100 m?
8. A profundidade declara **q e γ** e diz quais foram estimados?
9. A origem da contagem está correta (4.1.2.8 escavação / 4.1.2.9 estaca)?
10. Os critérios de parada (4.1.2.6 / 4.1.2.7, com o mínimo de 5 m) foram
    transcritos no plano, para o sondador em campo?
11. Foi recomendada investigação complementar quando o caso pede? A **nota de
    rodapé do item 4.1** prevê, na fase de projeto ou em estruturas especiais,
    programas específicos para resistência ao cisalhamento e compressibilidade.
