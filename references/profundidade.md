# Profundidade das sondagens — como o cálculo é feito

## 1. O que o gráfico da Figura representa

O item 4.1.2.2 fixa: parar onde o acréscimo de tensão devido às cargas for menor que
10% da tensão geostática efetiva.

    Δσ(D) = M · γ · D        com M = 0,1  (item 4.1.2.3)

O acréscimo no **centro** da área carregada vale `Δσ = q · I`, onde `I` é o fator de
influência de Boussinesq para retângulo uniformemente carregado. Igualando:

    q · I(D/B, L/B) = M · γ · D      →      q/(γ·M·B) = (D/B) / I(D/B, L/B)

que é exatamente o par de eixos do gráfico da norma. Por isso o script **não
digitaliza a figura**: resolve a equação, o que elimina erro de leitura em escala
log-log e cobre qualquer L/B, inclusive entre curvas.

`I` é obtido pela solução de Newmark para o canto de retângulo carregado, somada nos
quatro quadrantes (m = (B/2)/D, n = (L/2)/D):

    I_canto = 1/(4π) · [ 2mn√s/(s+m²n²) · (s+1)/s + arctan( 2mn√s/(s−m²n²) ) ]
    com s = m²+n²+1  e, quando m²n² > s, somar π ao arco-tangente
    I_centro = 4 · I_canto

Valores de aferição (batem com as tabelas clássicas): I_canto(0,5;0,5)=0,0840 ·
I_canto(1;1)=0,1752 · I_canto(1;2)=0,1999 · I_canto(2;2)=0,2325 · limite 0,25.

**Conferência no gráfico da norma:** informe sempre `q/(γMB)` e `D/B` na resposta —
o usuário entra com o primeiro no eixo vertical, sobe até a curva do seu `L/B` e lê
o `D/B` no eixo horizontal. Os dois devem coincidir com o que o script deu.

## 2. Definição de B, L, q e γ

| Símbolo | Definição da norma | Como obter |
|---|---|---|
| B | **menor** dimensão do retângulo circunscrito à planta da edificação | o script calcula o retângulo de área mínima sobre o polígono |
| L | **maior** dimensão do mesmo retângulo | idem |
| q | pressão média sobre o terreno = **peso do edifício / área em planta** | ver estimativa abaixo |
| γ | peso específico médio estimado dos solos ao longo da profundidade | ver tabela abaixo |
| M | 0,1 — coeficiente do critério 4.1.2.2 | fixo |

Atenção: B e L são do **edifício**. Se o polígono for o terreno, o retângulo
circunscrito superestima B e L e, com isso, a profundidade. Sinalize ou peça a
implantação (`--B` e `--L` permitem forçar os valores corretos).

### Estimativa de q quando o usuário não sabe
Ordem de grandeza usual em edifícios de concreto: **10 a 14 kPa por pavimento**
(cerca de 1,0 a 1,4 tf/m² por pavimento) sobre a área de projeção. O script usa
12 kPa/pavimento com `--pavimentos` (ajustável por `--q-pav`). Sempre declare que
é estimativa e que o valor correto vem do projeto estrutural — q entra linearmente,
então um erro de 30% em q desloca a profundidade de forma relevante.

### Estimativa de γ
| Solo | γ (kN/m³) |
|---|---|
| Aterro/argila mole saturada | 14 – 16 |
| Argila média a rija | 16 – 19 |
| Areia fofa a medianamente compacta | 17 – 19 |
| Areia compacta / solo residual | 19 – 21 |

Padrão do script: 18 kN/m³. Abaixo do nível d'água o correto é o **peso específico
submerso** (≈ γ − 10), porque o critério fala em tensão geostática **efetiva** —
com N.A. alto o D calculado cresce. Se o usuário informar nível d'água raso,
rode também com γ efetivo reduzido e apresente o valor mais conservador.

## 3. Da profundidade calculada à profundidade contratada

O `D` do critério é **um dos** limites. A profundidade a adotar é o maior entre:

1. `D` do item 4.1.2.2;
2. a cota necessária para atravessar todas as camadas impróprias ou questionáveis
   (nota do 4.1.2.1);
3. o mínimo imposto pelo tipo de fundação previsto;
4. quando se verifica a continuidade de camada impenetrável em fundação de
   importância: **5 m** dentro dela (4.1.2.7).

E é limitada pelos critérios de parada 4.1.2.6 e 4.1.2.7, que só se verificam em
campo. Redija sempre como "profundidade **prevista**, sujeita aos critérios de
parada", nunca como profundidade fixa.

### Origem da contagem
- Fundação rasa: da **superfície do terreno**, sem descontar escavação (4.1.2.8).
  Se haverá subsolo, a profundidade total do furo é maior que D.
- Fundação profunda: D é contado **da provável ponta da estaca / base do tubulão**
  (4.1.2.9). Profundidade total do furo ≈ cota prevista da ponta + D. Pergunte a
  cota prevista; sem ela, apresente a fórmula e não um número.

## 4. Exemplo resolvido

Edifício 30 × 40 m (1.200 m²), 10 pavimentos, γ = 18 kN/m³, fundação rasa:

- q ≈ 10 × 12 = 120 kPa; B = 30 m; L = 40 m; L/B = 1,33
- `q/(γ·M·B)` = 120/(18 × 0,1 × 30) = **2,22**
- Solução: `D/B` = 0,95 → **D ≈ 28,6 m** contados da superfície
- No gráfico: entrar com 2,22, interpolar entre as curvas L/B = 1 e 2, ler ≈ 0,95. ✓

Note a ordem de grandeza: prédios largos exigem furos profundos porque o bulbo de
tensões cresce com B. Se o resultado parecer alto, o dado a questionar é B (terreno
em vez de edifício) ou q, não o critério.
