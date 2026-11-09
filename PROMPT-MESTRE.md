# PROMPT MESTRE — Nest Battersea v2
## Para o Claude Code assumir o projeto

Cole este documento inteiro como primeira mensagem. Pasta de trabalho:
`C:\Users\berna\Desktop\NestBatterSea-LONDON`

---

# 0. LEIA ANTES DE TOCAR EM QUALQUER COISA

Existe uma v1 funcionando nessa pasta. Ela está **errada no núcleo** e vai ser
substituída. Antes de começar:

1. Leia `_refs/LEIA-ME.md` — tem o levantamento completo do empreendimento real.
2. Assista `_refs/videos-referencia/video1-referencia-planta3d.mp4` (extraia
   frames com ffmpeg) — é a referência da **planta 3D dollhouse** e da **barra
   de legenda do tour interno**.
3. Assista `_refs/videos-referencia/video2-referencia-flyin.mp4` — é a referência
   do **seletor de andar** e da **entrada de câmera no interior**.
4. Olhe `_refs/plantas-oficiais/fp-31.png`, `fp-32.png`, `fp-33.png` — são as
   plantas oficiais reais. **Toda a geometria 3D sai delas.**

Preserve `_refs/` intacta. Trabalhe numa pasta `v2/` e só promova para a raiz
quando estiver funcionando.

---

# 1. O PROBLEMA QUE VOCÊ ESTÁ RESOLVENDO

A v1 usa **vídeo gerado por IA** para o movimento de câmera da fachada até a
janela. Isso falhou e **não tem conserto por prompt**:

- A fachada muda de forma durante o voo. Lajes aparecem e somem, a silhueta
  muda, janelas se reorganizam.
- A câmera não chega no andar clicado. Não existe relação entre o clique e
  onde o vídeo termina.
- Cada unidade exigiria um vídeo novo (~10 créditos + 2 min + 11 MB).

**Causa raiz:** modelo generativo não tem o prédio. Ele sintetiza cada frame.
Travar primeiro e último frame não trava os 118 frames do meio.

**A decisão arquitetural desta v2:**

> O prédio vira **geometria 3D real** em Three.js, construída a partir das
> plantas oficiais. A câmera é uma câmera de verdade dentro dessa cena.
>
> Resultado: a fachada é matematicamente a mesma em todo frame porque é o
> **mesmo objeto**. Não há o que alucinar. A câmera vai ao andar 24 porque
> o andar 24 é `y = 24 * alturaDoPavimento`. A máscara da janela encaixa
> porque é a projeção da própria janela na tela.

**Não volte para vídeo generativo.** Se você se pegar pensando "talvez com um
prompt melhor o vídeo funcione" — não funciona, já foi testado, é o motivo
desta reescrita.

**Peso:** a torre inteira é geometria instanciada. Alvo: < 400 KB de geometria,
60 fps em notebook e ≥ 45 fps em celular de 2022. Isso é mais leve que os
21 MB de vídeo da v1, que devem ser **deletados** do build final.

---

# 2. DADOS REAIS — NUNCA INVENTE NENHUM DESTES

Fonte: documentação oficial, aplicação de planejamento Wandsworth 2025/0907.

## O edifício
| | |
|---|---|
| Nome | Nest Battersea |
| Endereço | 38 Lombard Road, Battersea, London SW11 3RP |
| Pavimentos | **34** |
| Altura | ~122 m (indicativo) |
| Residências | **143** (51 affordable) |
| Arquitetos | HTA Design LLP + Concrete (Amsterdam) |
| Incorporador | Heliport London Ltd (grupo Canada Israel) |
| Tenure | **Build to rent** — aluguel, não venda |
| Status | Em licenciamento, não construído |
| Vagas | Car-free |

## O conceito "Nest" — isto define o 3D
Não são apartamentos convencionais. São **sky homes** empilhados:
- **Bungalows** — casa de 1 pavimento, no céu
- **LOFTs** — casa de 2 pavimentos, pé-direito duplo

Cada uma com **jardim privativo plantado**. Nota literal das plantas oficiais:

> "For simplicity of explanation this plan shows all the double height lower
> plans at one same floor, but in reality each floor will have a mix of single
> and double-height homes."

**Consequência obrigatória para o 3D:** a torre não é 34 lajes iguais. É uma
mistura de pavimentos simples e duplos. Modele essa mistura — é a identidade
arquitetônica do prédio.

## As 6 posições por pavimento (01 a 06)

**Single height — Private** (`fp-33.png`):
| Pos | Nome | Config | Interior | Exterior |
|---|---|---|---|---|
| 01 | Bungalow 1 | 2b/3p | 61 m² | 10 m² |
| 02 | Bungalow 2 | 1b/2p | 51 m² | 9 m² |
| 03 | **Bungalow 3** | 2b/3p | **65 m²** | **15 m²** |
| 04 | Bungalow 4B | 2b/4p | 76 m² | 12 m² |
| 05 | Bungalow 5 | 2b/3p | 62 m² | 14 m² |
| 06 | Bungalow 6 | 1b/2p | 53 m² | 10 m² |

**Double height — Private** (`fp-31.png` lower + `fp-32.png` upper):
| Pos | Nome | Config | Interior | Exterior |
|---|---|---|---|---|
| 01 | LOFT 1 | 3b/5p | 100 m² | 10 m² |
| 02 | LOFT 2 | 2b/4p | 79 m² | 9 m² |
| 03 | LOFT 3 | 3b/6p | 112 m² | 15 m² |
| 04 | **LOFT 4** | 4b/7p | **134 m²** | **12 m²** |
| 05 | LOFT 5 | 3b/6p | 107 m² | 14 m² |
| 06 | LOFT 6 | 2b/4p | 86 m² | 10 m² |

**As duas unidades do demo: LOFT 4 e Bungalow 3.**

## O QUE NÃO EXISTE — não invente, não exiba
- **Preço / aluguel.** Nunca publicado. Build-to-rent. Não coloque valor
  nenhum na interface.
- Número de apartamento, andar específico por unidade, disponibilidade,
  vista por unidade, service charge, medidas cômodo-a-cômodo.

Onde a interface precisar de um andar (ex: "Level 24"), marque visivelmente
como posição ilustrativa. O painel deve continuar dizendo que não há valor
publicado.

## Marca
- Fonte: **Poppins** (200/300/400/500/600)
- Azul primário `#92B7CA` · hover `#C9E2EF` · escuro `#5D95B1`
- Texto `#4D4D4F` · quase-preto `#161922`
- Manter o tema **escuro** da v1. Decisão deliberada: é site de venda em cena
  noturna; luz acesa × apagada só funciona no escuro.

---

# 3. ARQUITETURA DA v2

```
v2/
  index.html
  src/
    main.js            bootstrap, máquina de estados
    tower/
      geometry.js      constrói a torre a partir dos dados das plantas
      floors.js        tabela de pavimentos: qual é simples, qual é duplo
      units.js         6 posições × tipologia → volume, janela, jardim
      materials.js     concreto, madeira, vidro, vegetação
      lights.js        luz de interior por unidade (acesa / apagada)
    camera/
      rig.js           câmera com waypoints, damping, easing
      paths.js         gera o trajeto fachada → janela → interior
    interior/
      build.js         extruda o interior 3D a partir da planta
      dollhouse.js     modo axonométrico rotacionável (video 1)
      walkthrough.js   modo câmera em primeira pessoa (video 2)
    ui/
      rail.js          seletor de residência
      panel.js         painel da unidade
      plan.js          tela da planta
      transitions.js   todas as transições
      sound.js         (opcional) ambiência sutil
    data/
      building.js      TODOS os dados da seção 2 deste documento
  assets/
    hdri/              environment map para reflexos no vidro
    textures/          concreto, madeira, vidro, vegetação
    interiors/         renders para os quadros do tour (reaproveitar da v1)
    plans/             plantas oficiais recortadas (reaproveitar da v1)
```

**Stack:** Three.js (r160+) + GSAP. Sem framework de UI — vanilla.
Bundler: Vite. Não use React, não precisa.

---

# 4. A TORRE EM 3D

## 4.1 Construa a partir da planta, não do olho

As plantas oficiais têm **escala gráfica (0-1-2-5 m)** e **rosa dos ventos**.
Use-as. Meça o footprint real em metros e modele nessa escala. O prédio tem
um formato irregular em planta — um quadrilátero com um canto cortado em
diagonal na face oeste. **Reproduza esse formato.** Não faça uma caixa.

Pé-direito: as plantas confirmam "tall ceilings". Use ~3,2 m para pavimento
simples e ~6,4 m para o duplo. 34 pavimentos ≈ 122 m fecha.

## 4.2 Elementos obrigatórios da fachada

Olhe `_refs/cgi-oficial/tower-night.png` e `01-night-river.jpg` em zoom:

- **Estrutura de concreto aparente** — lajes horizontais contínuas e
  pilares, formando uma grelha empilhada.
- **Madeira clara nos forros e reveals** — brilha dourado quando a unidade
  está acesa. É a assinatura visual do prédio.
- **Varandas projetadas e recuadas alternadamente**, com laje grossa na borda.
- **Vegetação densa em todas as varandas** — arbustos, gramíneas, árvores
  pequenas, trepadeiras transbordando. Use instanced meshes com billboards
  cruzados; não precisa de folha modelada.
- **Vidro de piso a teto com montantes verticais finos e escuros.**
- **Coroamento:** jardim no topo cercado de **lâminas verticais de madeira**
  com árvores acima do último pavimento.
- **Base:** podium comercial térreo. O pavilhão vermelho vizinho é marcante
  no CGI real — inclua no entorno.

## 4.3 Entorno

Não precisa modelar Londres. Faça blocos simples com janelas emissivas nas
posições certas, conferindo com `05-cgi-a.jpg`:
- Torre de vidro azul-escuro curva **à esquerda** (Riverlight)
- Blocos curvos creme/claros **à direita**
- Pavilhão vermelho na base
- Píer do heliporto e muro de tijolo do Tâmisa
- Plano d'água com reflexo (pode ser um plano com normal map animado leve)
- Céu de blue hour: gradiente índigo no alto, faixa quente no horizonte

**Opção de performance:** use `tower-4k.jpg` como *backdrop* fotográfico para
o entorno distante e modele em 3D apenas a torre + os dois vizinhos imediatos.
Isso mata 80% do custo de render. Avalie e decida.

## 4.4 Luzes acesas e apagadas

Cada unidade tem um estado: `available` (acesa) ou `let` (apagada).
Acesa = material emissivo quente no interior visível + glow no forro de madeira.
Apagada = escura, levemente refletindo o céu.

Distribua as apagadas de forma **irregular e sem padrão**, como prédio real.
O estado vem de `data/building.js`, não da geometria — trocar o estado de uma
unidade tem que ser mudar uma linha de dado.

---

# 5. A MÁSCARA DA JANELA — resolver o problema da imagem

**Problema atual:** a máscara é um polígono desenhado à mão que não bate com a
janela. Olhe o print que o cliente mandou: a forma vaza.

**Solução:** a máscara deixa de ser desenhada. Ela passa a ser a **projeção da
própria geometria da janela**.

Para cada unidade, o modelo já tem o mesh do vão envidraçado. Para desenhar o
destaque:
1. Pegue os vértices do contorno do vão.
2. Projete na tela com `vector.project(camera)`.
3. Monte o `<polygon>` do SVG com esses pontos, atualizado a cada frame.

Encaixa perfeitamente por construção, em qualquer ângulo, em qualquer zoom.
Nunca mais vai vazar.

**Estados do destaque:**

| Estado | Comportamento |
|---|---|
| Repouso (disponível) | Glow quente suave pulsando devagar no vão |
| Hover | Contorno `#92B7CA` 1,5px aparece em 300ms · interior clareia · **o resto da torre escurece ~35%** · etiqueta com nome e tipologia |
| Selecionada | Contorno fica sólido · leve halo · a unidade permanece destacada durante todo o voo |
| Apagada (let) | Escura, cursor normal, etiqueta diz "Let", não clicável |

O pedido do cliente de "destacar mais o apartamento" se resolve com o
**escurecimento do resto da torre no hover**. É o recurso mais forte e mais
elegante: em vez de gritar no apartamento, você silencia o resto.

---

# 6. O MOVIMENTO DE CÂMERA

## 6.1 Regra inegociável

A fachada **não pode mudar** entre o início e o fim. Com 3D isso é automático:
é o mesmo mesh. Não aplique nenhum efeito que reescreva a imagem
(nada de img2img, nada de pós-processamento generativo).

## 6.2 Chegar no andar certo

```js
const y = floors.baseHeight + floors.offsetOf(unit.floorIndex) + unit.eyeHeight;
const target = unit.windowCenter;   // ponto no mundo, vem da geometria
```

Se o usuário clicou no LOFT 4 do pavimento 24, a câmera para na frente do
LOFT 4 do pavimento 24. Determinístico. Teste isso explicitamente: clique em
cada unidade e verifique que `camera.position.y` corresponde ao andar.

## 6.3 O trajeto

Use uma `CatmullRomCurve3` com 3 waypoints:

1. **Início** — posição estabelecida da fachada, longe, do outro lado do rio.
2. **Meio** — um ponto deslocado lateralmente, na altura intermediária.
   Esse desvio é o que cria **parallax real**: os prédios da frente passam
   pelas bordas do quadro. É o que vende a sensação de câmera de verdade.
3. **Fim** — flutuando a ~12 m da janela, na altura do olho da unidade.

Duração 2,6 s a 3,2 s. Easing `power3.inOut`. A câmera olha sempre para um
alvo que interpola suavemente do centro da torre para o centro da janela —
nunca gire a câmera bruscamente.

**A volta é a mesma curva com `t` invertido.** Não é animação nova. Mesmo
caminho, para trás. 2,2 s, um pouco mais rápido que a ida.

## 6.4 Qualidade de movimento (isto é o "luxo")

- Damping na câmera: nada de parada seca. Um leve overshoot de ~2% e
  assentamento.
- **Depth of field** sutil via postprocessing — foca na janela ao chegar,
  desfoca o fundo. É o que mais faz parecer cinema.
- Micro-movimento de respiração quando parada (amplitude < 0,3°).
  Faz a cena parecer viva em vez de congelada.
- Trave em 60 fps. Se cair abaixo de 50, reduza qualidade de sombra
  automaticamente, nunca deixe engasgar.
- `prefers-reduced-motion`: corta direto, sem voo.

---

# 7. FLUXO DO SITE

```
TORRE ──click na janela──► VOO ──► UNIDADE
  ▲                                 │  │
  └────── voo reverso ──────────────┘  │
                                       ├──► PLANTA 3D (dollhouse, igual video 1)
                                       └──► INTERIOR (câmera entra, igual video 2)
```

## 7.1 TORRE (estado inicial)
- Torre 3D navegável. Órbita limitada com o mouse (±18° horizontal, ±10°
  vertical) com damping forte — dá vida sem deixar o usuário se perder.
- Barra de navegação em pílula no topo, legenda e CTA embaixo.
- **Rail de seleção à direita** — igual ao "Choose your floor" do video 2.
  Listar as duas residências. Hover no rail destaca a janela na torre e
  vice-versa. Os dois sentidos.
- Título à esquerda. Entrada com as linhas subindo em máscara.

## 7.2 UNIDADE (depois do voo)
Câmera parada na frente da janela, DOF ativo, unidade iluminada.
Painel lateral com: nome, tipologia, posição, ocupação, área interna,
área do jardim privativo, pé-direito. **Sem preço.**
Dois botões: `Floor plan` e `Step inside`.

## 7.3 PLANTA 3D — dollhouse (referência: video 1)

**Não é a imagem da planta inclinada.** Isso foi a v1 e é insuficiente.

Construa o **interior 3D de verdade**:
1. Trace os polígonos das paredes a partir da planta oficial (`fp-31/32/33`).
   Faça isso uma vez, à mão, em coordenadas métricas, e guarde em
   `data/building.js`.
2. Extruda as paredes até ~1,1 m (corte de dollhouse — paredes baixas para
   a câmera enxergar dentro). **Sem teto.**
3. Piso com material por ambiente (madeira na área social, pedra nos
   molhados) — espelhando as cores da planta oficial.
4. Mobiliário em volumes simples e limpos: sofá, mesa, camas, cozinha,
   louças. Não precisa de detalhe — precisa ser legível de cima.
5. Vegetação na varanda.
6. Câmera axonométrica. **Arrastar rotaciona.** Inércia ao soltar.
7. Rótulos flutuantes por ambiente com área, aparecendo em stagger.
8. Para o LOFT 4: toggle **Lower floor / Upper floor**, com os dois níveis
   deslizando na vertical na troca — mostra que é pé-direito duplo.

Entrada da tela: a planta sobe e assenta em rotação, igual o video 1.

## 7.4 INTERIOR — walkthrough (referência: video 2)

A câmera **atravessa o vidro** e entra. Não corta.

1. Da posição da UNIDADE, a câmera avança pela janela.
2. O vidro faz fade de opacidade enquanto ela passa.
3. Por dentro, percorre uma curva passando pelos ambientes.
4. Em cada parada, **barra de legenda embaixo** (igual video 1): índice,
   nome do ambiente, setas e dots. `Living & Kitchen`, `Principal Bedroom`,
   `Principal Bathroom`, `The Garden`.
5. Setas e teclado navegam entre as paradas; a câmera **desliza** entre
   elas, nunca corta.

**Implementação dos ambientes:** use os renders em `assets/interiors/`
projetados em planos posicionados na geometria do interior 3D, com a câmera
se movendo entre eles. Isso te dá qualidade fotográfica com custo de
geometria quase zero. Alternativa: iluminar e renderizar o interior 3D
direto, se a qualidade ficar boa.

## 7.5 Interiores DIFERENTES por tipologia — requisito explícito

O LOFT 4 e o Bungalow 3 **não podem mostrar as mesmas imagens**. São
tipologias diferentes e o cliente notou isso.

- **LOFT 4** — 134 m², 4 quartos, **pé-direito duplo com mezanino**.
  O interior tem que mostrar o volume de dois pavimentos e a escada.
  A imagem `assets/interiors/living.jpg` da v1 já tem mezanino: serve.
- **Bungalow 3** — 65 m², 2 quartos, pavimento único, jardim de 15 m²
  (o maior jardim entre os bungalows — destaque isso).
  Precisa de imagens próprias: ambiente menor, pé-direito normal, foco na
  relação com a varanda plantada.

Gere os renders que faltarem. Mantenha a mesma linguagem: carvalho claro,
concreto aparente, linho, travertino, blue hour pela janela.

---

# 8. ACABAMENTO — "classe e luxo"

Este site é ferramenta de corretor. O público decide com os olhos.

**Todo botão responde.** Nada pode parecer morto:
- `Register interest` → abre painel com formulário, não `alert()`
- Itens do menu → levam a seções reais ou abrem overlay
- Hover em qualquer elemento clicável → resposta em até 150 ms
- Estado de foco visível para teclado

**Transições:** nada aparece ou some de repente. Tudo tem entrada e saída.
Use uma escala única de duração (180 / 320 / 640 / 1200 ms) e uma curva
única, e não invente outras.

**Tipografia:** respeite a escala. Peso 200 nos títulos grandes, 500 nas
etiquetas em caixa alta com tracking largo. Não encha a tela de texto.

**Loading:** a cena 3D leva tempo. Tela de carregamento com a marca e
progresso real (não falso). Entre na cena com um movimento lento de câmera
já rodando — o usuário nunca vê um frame parado.

**Som (opcional, desligado por padrão):** um toggle discreto com ambiência
de cidade ao longe. Se fizer, tem que ser elegante ou não faça.

**Mobile:** funciona de verdade. Toque em vez de hover para o destaque da
janela: primeiro toque destaca e mostra a etiqueta, segundo toque entra.
Rail vira lista embaixo. Reduza sombras e DOF.

---

# 9. CRITÉRIOS DE ACEITE

Teste cada um e me mostre a evidência.

- [ ] A fachada no frame 0 e no último frame do voo é **a mesma geometria**.
      Prove: screenshot do início e do fim com a torre na mesma posição
      relativa, sem diferença estrutural.
- [ ] Clicar no LOFT 4 leva a câmera ao pavimento do LOFT 4. Clicar no
      Bungalow 3 leva ao pavimento do Bungalow 3. Pavimentos **diferentes**.
- [ ] A máscara de hover acompanha o contorno do vão envidraçado em qualquer
      ângulo de órbita e em qualquer ponto do voo.
- [ ] No hover, o resto da torre escurece visivelmente.
- [ ] O voo de volta refaz o mesmo caminho e termina no enquadramento inicial
      exato.
- [ ] A planta abre como **interior 3D rotacionável**, não imagem inclinada.
- [ ] O LOFT 4 tem toggle de dois pavimentos funcionando.
- [ ] "Step inside" atravessa o vidro com a câmera, sem corte.
- [ ] LOFT 4 e Bungalow 3 mostram interiores **diferentes**.
- [ ] Nenhum preço em lugar nenhum da interface.
- [ ] Todo botão visível faz algo.
- [ ] ≥ 50 fps em notebook, ≥ 40 fps em celular de 2022.
- [ ] Build total < 12 MB (os MP4 da v1 saem).
- [ ] Zero erro no console durante o fluxo completo.

---

# 10. ORDEM DE TRABALHO

1. Extraia a geometria das plantas oficiais para `data/building.js`.
   **Esta é a fundação. Faça com cuidado, confira com a escala gráfica.**
2. Torre 3D + materiais + luzes acesas/apagadas. Pare e valide contra
   `_refs/cgi-oficial/tower-night.png` lado a lado.
3. Projeção da máscara de janela + hover + escurecimento do resto.
4. Rig de câmera + trajeto + ida e volta. Valide o andar exato.
5. Painel da unidade.
6. Dollhouse 3D do interior.
7. Walkthrough.
8. Acabamento, som, mobile, performance.

**Pare depois do passo 2 e depois do passo 4 e me mostre.** São os dois
pontos onde erro estrutural fica caro.

---

# 11. SE ALGO NÃO FOR POSSÍVEL

Fale. Não entregue uma aproximação silenciosa, e principalmente **não volte
para vídeo generativo** como atalho. Se a modelagem do interior a partir da
planta ficar grande demais, diga e proponha recorte — por exemplo, fazer o
dollhouse só do LOFT 4 na primeira entrega.

Fidelidade acima de completude. Um apartamento perfeito vale mais que dois
aproximados.
