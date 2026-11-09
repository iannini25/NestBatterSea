# Direção de imagem e vídeo | Nest Battersea

Como foram feitos os voos, as entradas, as fotos dos interiores e a planta 3D, com os prompts exatos. Serve para refazer, ajustar ou criar um terceiro apartamento.

## O princípio

**A câmera só se move; nada no prédio, no entorno ou no apartamento pode mudar, e ela vai exatamente para a janela clicada.** Duas tentativas com vídeo de IA não cumpriram isso. Na primeira, o Kling tinha início e fim travados na imagem oficial. Na segunda, a chegada foi gerada de frente com a janela aberta. Nos dois casos a IA reinterpretou a fachada, e na segunda também mexeu nos móveis do interior. Por isso os movimentos agora são feitos sem IA nenhuma.

## Voo e Step inside: híbrido, câmera exata + IA só na chegada (versão atual)

O cliente pediu um movimento de câmera de verdade até a janela clicada, terminando reto nela, nivelado no meio da altura (dá para ver o chão e o teto da sala), com a imagem final sendo a janela vista de fora, nítida e sem máscara recortada. Ele também liberou a IA para completar o que a imagem oficial não mostra, sem mudar o prédio.

- **Parte A, exata (sem IA), `_work/flight/render_part_a.py`.** É o mesmo caminho da prévia (`render_previz.py`): a imagem oficial em camadas 3D (`proxy.py`), com a câmera atravessando o rio, subindo e girando.
  - Vai até onde os pixels oficiais ainda estão nítidos. No LOFT 4 é 45% do caminho, no Bungalow 3 é 30%, porque a face da direita aparece quase de lado na imagem oficial.
  - Sai a 60 fps, com desfoque de movimento, e grava o quadro de passagem (`out/hybrid/<casa>-seam.png`).
- **Quadro final (IA de imagem).** GPT Image 2.6, qualidade alta, 2K, a 2,75 créditos. As referências são:
  - a prévia do fim (enquadramento exato) ou o modelo 3D da planta visto de fora (`_work/ai/shot-ext.mjs`);
  - o recorte oficial nítido da fachada;
  - o quadro final do outro apartamento, para manter o mesmo estilo;
  - a foto da sala, que aparece pelo vidro.

  Para o LOFT 4, a árvore, o guarda-sol e a luminária caíram nas posições da imagem oficial com erro de 1%. No Bungalow 3, foi preciso dizer explicitamente que a torre continua acima e abaixo da casa.
- **Parte B, aproximação final (IA de vídeo).** Kling 3.0 Pro, a 7,5 créditos por 5 s, com o quadro de passagem como primeiro quadro e o quadro final como último. O Kling caiu exatamente no quadro final (deslocamento de 0,0 px).
- **Montagem, `_work/ai/assemble.py`.**
  - A parte B é reamostrada pelo zoom medido, para a velocidade continuar a da parte A na emenda (LOFT 4: 0,77 → 0,76 log/s) e frear suave na janela.
  - Os quadros intermediários a 60 fps vêm de fluxo óptico.
  - Os últimos quadros deslizam até o alinhamento e se dissolvem no quadro final exato.
- **Step inside.** Kling 3.0 Pro, do quadro final até a foto da sala, entrando pela porta de correr aberta. Começa exatamente no quadro final e termina exatamente na foto: no LOFT 4, um deslizamento de 11 px até o registro.
- **Guias.** A prévia da câmera (`render_previz.py`) e o voo pelo modelo 3D até a pose da foto (`_work/ai/flythrough.mjs`) ficam como guia e conferência.
- **Por que não Genjutsu ou Wan com vídeo guia:**
  - O Genjutsu custa 100 créditos por clipe de 5 s em 1080p, ou 35 em 720p.
  - O Wan 3.0 não aceita primeiro e último quadro junto com vídeo de referência.
  - O Seedance 2.5 custa 80 em 1080p.
  - O Kling com quadros travados, numa aproximação curta (×2), já entrega o movimento sem alucinar.

## Versão anterior: câmera 3D sobre a imagem oficial (sem IA)

Tudo em `_work/flight/`. Um zoom reto (2D) foi recusado: o cliente quer um movimento de câmera de verdade, que leve exatamente até a janela e termine reto nela, com a volta pelo mesmo caminho.

- **`proxy.py`: a imagem oficial em camadas 3D.**
  - A imagem é separada em céu, prédios da outra margem, as duas faces da torre e o rio.
  - Cada camada vai para um plano em 3D, visto pela própria câmera do render. A calibração é: câmera nivelada, horizonte em y 1250, f 8000 px, e as linhas da face NE convergindo em x 3356. A face SE fica a 14,5 graus de frente e a NE quase de lado.
  - Uma câmera virtual avança, sobe e gira, e cada quadro reprojeta os pixels oficiais por esses planos. Só o ponto de vista muda. A fachada mantém o desenho exato, e a perspectiva, as lajes e a paralaxe contra o céu mudam como num voo de drone.
  - Atrás dos prédios, onde a câmera passa a ver ao subir, entra um modelo suave do próprio céu oficial. O brilho em volta dos prédios acesos é uma camada que viaja com eles, então não fica contorno fantasma no céu.
- **`render_flight3d.py`: o voo, 4 s a 60 fps.**
  - A câmera atravessa o rio, gira em direção à fachada e sobe.
  - Ela mantém a altura oficial enquanto o rio e a outra margem estão no quadro. Depois sobe pela linha que deixa a borda de baixo do quadro 0,3 grau acima do horizonte. Assim tudo o que aparece existe na imagem oficial, e nunca surge o chão atrás da margem, que nenhuma imagem mostra.
  - A câmera nunca inclina, então as verticais ficam verticais.
  - **LOFT 4:** termina de frente para a fachada SE (gira 14,5 graus), reto na janela e um pouco abaixo dela.
  - **Bungalow 3:** a face NE aparece quase de lado na foto oficial. A câmera gira 7,7 graus em direção a ela, porque mais do que isso esticaria a fachada além do que os pixels oficiais têm, e termina nivelada com a casa.
  - **A janela abre no último segundo.** Os painéis de vidro (máscaras de `glass_masks.py`, presas ao plano da fachada) passam a mostrar a foto da sala. A foto fica num plano 60 unidades atrás do vidro, com paralaxe leve, e chega na mesma escala de antes.
  - O script grava `out/<casa>-track3d.json`, com a caixa da janela e a homografia da fachada de cada quadro. `write_tracks.py` transforma isso em `js/tracks.js`, e o contorno do site segue a janela em perspectiva.
- **`render_inside3d.py`: o Step inside, 2,6 s.**
  - Começa exatamente no último quadro do voo, e a mesma câmera continua avançando até o vidro.
  - A fachada passa pela lente e desfoca, e a foto termina em tela cheia, sem alteração.
- **Tudo de uma vez:** `bash _work/flight/run_all3d.sh` renderiza os quatro clipes, codifica e escreve as tracks.
- **Volta:** é o mesmo arquivo invertido.

### A versão anterior (zoom 2D, substituída)

- **Fontes, sempre oficiais.**
  - A imagem que o site mostra vem do render noturno original do site deles, `2153_031_72_00-1-1.jpg`, com 4204 x 3153. É 64% maior que a versão de 2560 usada antes.
  - Para a aproximação usamos o render de perto da torre, `tower-night.png`, que tem o dobro de densidade. Ele foi alinhado ao original por ECC com correlação 0,9989, ou seja, é o mesmo render. Usamos a ampliação 3,18x dele (`_work/frames/tower_up.png`).
  - Erro de alinhamento: menos de 0,1 px. Cor: idêntica.
- **`camera.py`** desenha qualquer enquadramento (centro e largura) a partir dessas fontes, com pirâmide de imagens: amostragem trilinear para reduzir e bicúbica para ampliar.
- **`render_flight.py`** faz o voo de 4 s a 60 fps.
  - Caminho de pan e zoom suave (van Wijk), com um leve arco lateral e curva de velocidade cubic-bezier (0.5, 0, 0.25, 1).
  - Desfoque de movimento de 7 subquadros por quadro.
  - Termina centrado exatamente na caixa da janela, com largura de 130 px da imagem 2560.
  - Grava `js/tracks.js` com a caixa da janela e a câmera de cada quadro. Com isso, o contorno da janela fica preso nela durante o voo inteiro.
- **`glass_masks.py`** mede a grade de montantes da caixilharia e monta a máscara dos painéis de vidro de cada casa no quadro de chegada. A árvore, o guarda-sol, as plantas e a luminária ficam na frente.
- **A janela abre na chegada (`interior.py`).** No último segundo do voo, enquanto a câmera pousa, os painéis de vidro da casa passam a mostrar a sala por trás.
  - A árvore, o guarda-sol, a floreira e os caixilhos continuam na frente. A luminária do jardim mantém o brilho por cima.
  - Um painel fica totalmente aberto, e os outros guardam 18% do reflexo original.
  - A sala entra na escala real: vista de longe, com a lente longa do render oficial, ela aparece quase na escala da própria fachada. No LOFT 4, a fachada tem cerca de 4 m a 170 px/m, e a parede do fundo fica 7,7 m atrás do vidro. Por isso a foto entra a 0,88 da tela, e a 0,86 no Bungalow 3.
- **`render_inside.py`** faz o Step inside de 2,6 s.
  - A câmera continua avançando para o vidro, e a sala aparece pelos painéis reais.
  - A fachada desfoca e sai de quadro.
  - Termina exatamente na foto da sala (escala 1, sem deslocamento). A foto não é alterada em nada.
- **Acabamento:** `python _work/finish_video2.py <master.mkv> <slug> --fps 60 --sharpen 0 --no-qc --out assets` gera H.264 e AV1, 1080p e 720p, ida e volta e os stills.
- **Resultado medido:**
  - Primeiro quadro contra a imagem da torre no site: 2,7/255.
  - Último quadro contra a foto de chegada: 2,2/255.
  - Peso do voo: 2,8 MB em H.264 e 1,3 MB em AV1, contra 5,6 MB do voo com IA.

## O modelo 3D da planta (base de tudo)

`_work/plan3d/src/apartments.js` tem cada parede, janela, cômodo, móvel e jardim dos dois apartamentos em pixels das plantas oficiais `fp-31`, `fp-32` (LOFT 4) e `fp-33` (Bungalow 3). A escala da barra gráfica é de 44,4 px por metro.

- **LOFT 4:** dois andares. O piso do andar de cima pousa exatamente sobre as paredes do de baixo. A escada em U tem degraus em leque e 17 espelhos de 0,188 m, chegando a 3,2 m no patamar de cima. O vazio do pé-direito duplo tem aletas de carvalho no quarto três e guarda-corpo de vidro na galeria.
- **Bungalow 3:** um andar, com o jardim triangular de 15 m² do lado noroeste e a floreira estreita do lado nordeste. Na fachada nordeste não existe varanda, só a floreira.
- **Como roda:** o mesmo código serve a planta 3D do site (`assets/js/plan3d.js`, empacotado por `_work/plan3d/build-bundle.cjs`) e as vistas guia (`node _work/plan3d/shot.mjs`). A prévia fica em `http://localhost:8080/_work/plan3d/preview.html`.

## Ferramentas e custos

| Uso | Ferramenta | Custo |
|---|---|---|
| Voos e Step inside | câmera virtual própria sobre as imagens oficiais (`_work/flight`) | zero crédito |
| Fotos dos interiores (4 por imagem) | GPT Image 2.6 no Higgsfield, 4K, qualidade média, grade 2x2 | 1,25 crédito por grade |
| Ilustrações da região (lago, Power Station, Northcote Road, orla) | GPT Image 2.6, 4K, grade 2x2 | 1,25 crédito |

**Fora:**
- Vídeo por IA para o prédio: Kling e Genjutsu reinterpretam a fachada.
- Quadros de chegada gerados por IA.
- Interpolador RIFE: o ambiente bloqueou executável baixado. A suavização das cenas antigas usava fluxo óptico em `_work/finish_video2.py`, e as novas já saem a 60 fps.

## Pipeline das fotos

1. `node _work/plan3d/shot.mjs <saída> <casa> <jobs>` renderiza cada pose em 1920x1080, com teto, luminárias acesas e noite lá fora.
2. `python _work/photos/grid.py build gridX.jpg a.png b.png c.png d.png` monta 4 vistas numa imagem 4K com calhas pretas.
3. GPT Image 2.6 transforma a grade em fotos (prompt abaixo).
4. `python _work/photos/grid.py split saída.png nomes pasta` separa de volta em 1920x1080.
5. Publicação em `assets/interiors/<id>.jpg`, `.webp` e `.avif`.

Só os cômodos principais têm foto. Banheiros de 1 m de profundidade, halls, depósitos e closets ficam no 3D sem foto, como na referência.

### Prompt das grades (exemplo, salas)

```
The reference image is a 2 by 2 grid of four separate interior views, rendered from a precise 3D model of two apartments in a London residential tower, built from the architect's floor plans. Turn EACH of the four panels into a real architectural interior photograph. Keep the same 2 by 2 layout with the same thin black gutters: four separate photographs, one per panel, nothing crossing from one panel into another.

In every panel keep EXACTLY what the render shows: the camera position, height, lens and perspective; every wall, opening, column and ceiling edge; every window, its slim dark bronze frames and glazing bars, and the open sliding door; the double height space, the tall vertical oak fins on the upper floor and the gallery with its glass balustrade; every piece of furniture in the same place with the same size, shape and colour: [lista de móveis e cores]. Do not add, remove or move any object, do not change any colour, do not redesign anything.

Make it photographic: real materials with fine texture (...), soft warm 2700K light from the downlights, pendants and lamps, gentle natural shadows and bounce light, realistic depth and lens rendering. Through the windows: London at blue hour, ten minutes after sunset, deep blue sky, distant city lights and the river; outside the glass, the planted garden terrace with lush green shrubs and a small tree, softly lit.

[uma frase por painel descrevendo o cômodo]

Style: high end residential launch photography, true colours, natural contrast, sharp, calm and inviting. No people, no text, no logos, no watermarks, no CGI look.
```

### Prompt da chegada (LOFT 4; o do Bungalow 3 troca o andar e os elementos)

```
Three references. Image 1 is the exact shot to reproduce: camera position, height, lens, framing and the position of every element. Image 2 is the official architect's render of the same tower, Nest Battersea in London: use it for the exact facade design, materials and night lighting. Image 3 is the living room inside this home: use it for what is seen through the glass.

Make a real architectural photograph of image 1: a camera hovering level with the 23rd and 24th floors at blue hour, about ten metres in front of one double height loft home, looking straight at it, horizon level, all verticals perfectly vertical, no tilt.

Keep exactly as in image 1: on the left, a full height solid wall clad in dark bronze. In the centre, the two storey glass wall in slim dark bronze frames, with a horizontal bronze transom at the upper floor level; behind the upper glass, the tall vertical oak fins of the bedroom gallery inside the warm double height room. At the lower level, one large sliding glass panel stands fully open, slid to the right behind the next fixed panel, so the doorway is clear and the warm living room is seen directly through it (...). In front, a narrow planted garden (...). Above, the slab of the floor above with its dark bronze edge and warm timber soffit. On the right, the corner of the tower and the night sky over London.

Facade design exactly as image 2 (...). Light: blue hour (...). Full frame camera, 35mm lens, f/5.6 (...). Avoid: looking up at the building, tilted verticals, distortion, extra balconies or floors in front of the home, a closed glass wall, people, birds, text, logos, lens flare, CGI look.
```

## Regras que valem daqui em diante

1. **Nada gerado no prédio.** Voo e entrada são câmeras virtuais sobre as imagens oficiais. IA só nas fotos de interior e nas ilustrações da região, sempre marcadas como ilustrativas.
2. **A janela é um retângulo medido**, não uma descrição em texto: a caixa em `js/data.js` define o fim do voo e o contorno que a acompanha.
3. **As fotos de interior saem do modelo 3D** feito das plantas oficiais, para cores, móveis e janelas baterem com a planta.
4. **Ida e volta são o mesmo arquivo invertido.** A volta refaz exatamente o caminho.

## Para um terceiro apartamento

1. Transcrever a planta em `apartments.js` (paredes, portas, vidros, cômodos, móveis e as poses das fotos).
2. Renderizar as vistas guia (`shot.mjs`) e gerar as fotos em grade 2x2 com o prompt acima.
3. Marcar o vão na imagem oficial e adicionar a casa em `js/data.js` e em `HOMES` de `render_flight3d.py`, com a face (SE ou NE), o quanto girar e a distância de chegada. Depois desenhar a máscara do vidro em `glass_masks.py` e o ponto de mira em `interior.py`.
4. Rodar `run_all3d.sh` (ou `render_flight3d.py`, `render_inside3d.py`, `finish_video2.py` e `write_tracks.py`) e conferir as emendas.

## Voo LOFT 4 e Step inside sem vídeo de IA (v24, 9 nov 2026)

Regra do cliente, acima de todas: **só a câmera se move**. Nada no prédio ou no apartamento pode mudar
durante um vídeo (nada "se construindo", cadeiras que mudam, ambiente que muda de tamanho).

**Voo LOFT 4** (`_work/flight/render_full.py`): câmera virtual exata do início ao fim, sem Kling.
- Imagem oficial em planos (`proxy.py`) + imagem final da janela registrada no plano da fachada SE
  (ECC sobre o previz, `out/hybrid/loft4-key-A.npy`) como camada nítida.
- A imagem final é dividida em duas camadas (`_work/inside3/l4_layers.py`): F = fachada, caixilhos,
  árvore, guarda sol, jardineiras (máscara por zonas e cor); R = a sala (versão da mesma foto sem o
  primeiro plano, GPT Image, registrada) num plano 25 unidades atrás, com as bordas da sala estendidas
  (teto, piso, paredes) para o que se vê de lado. A sala acesa, com o mezanino, já está lá desde o
  início (entra nos primeiros 0,6 s, com a janela de poucos pixels: a luz acendendo).
- `GLOW_FADE` + `TOWER_MATTE` (opt in em `proxy.py`): o céu oficial fica no infinito, o céu entre as
  varandas não viaja com a torre, a borda azulada (bloom) da silhueta é removida. Era a "camada em
  volta do prédio".
- Tempo: o caminho é reparametrizado para que a velocidade percebida seja um único sino (smootherstep).

**Step inside, LOFT 4 e Bungalow 3** (`_work/inside3/render_inside.py`): câmera real sobre as duas
camadas F e R vistas da câmera final do voo; frame 0 = último frame do voo (MAD 0,1). A câmera atravessa
a linha da fachada por um ponto livre (B3: a porta de correr aberta, acima da jardineira; LOFT 4: um
painel livre acima à direita, longe da árvore e do guarda sol), com lens shift (verticais retas), e
termina com a sala enchendo o quadro. A sala é ampliada uma vez (upscale Higgsfield, 2 créditos) só
para nitidez. O último frame vira a foto `loft4-living` / `bung3-living` (primeira do tour).
