# Nest Battersea | site

A torre é o **CGI oficial** do empreendimento. As duas residências disponíveis (LOFT 4 e Bungalow 3) estão marcadas exatamente sobre o vão de cada uma. Ao clicar, um movimento de câmera leva até aquela janela, e o contorno da janela acompanha o vão quadro a quadro durante o voo. "Step inside" atravessa o vidro e termina exatamente na foto da sala. Abaixo do cartão, dez seções contam o projeto inteiro: visão, vistas oficiais, as duas casas, as doze tipologias, affordable, acessibilidade, sustentabilidade, localização com mapa, próximos passos e contato.

Direção de imagem, prompts e validação dos vídeos: [DIRECAO.md](DIRECAO.md). Fontes de todo o texto: [_work/content/sources.md](_work/content/sources.md).

## Abrir

```bash
cd NestBatterSea-LONDON
python -m http.server 8080
```
Abra `http://localhost:8080`. É preciso servidor (os vídeos, o mapa e a planta 3D não carregam direto do disco).

## Estrutura

```
index.html, css/app.css, js/app.js   o site: palco, seções, lightbox, abas das plantas, lista de lugares
js/motion.js                         todo o movimento de rolagem (GSAP 3.12.5 + ScrollTrigger, cdnjs)
js/map.js                            o mapa da Localização (MapLibre GL 4.7.1, cdnjs) com estilo próprio
js/notch.js                          o contorno com recortes (clip-path em SVG), do cartão principal e dos cartões das seções
js/data.js                           residências, cômodos com foto e legendas, tipologias, HANDOFF da entrada
js/tracks.js                         GERADO com os vídeos: a janela de cada quadro do voo (FLIGHT_TRACKS)
assets/js/plan3d.js                  planta 3D "dollhouse" (Three.js), carregada só quando a planta abre
assets/facade, assets/video, assets/stills, assets/interiors, assets/plans, assets/brand
assets/site/views                    as vistas oficiais (bordas de régua recortadas), AVIF/WebP/JPG em 640, 1280 e 1868
assets/site/plans                    plantas oficiais com o fundo verde trocado por papel, mais o diagrama ambiental
assets/site/vision, res, area        imagens das seções (area = ilustrações IA do bairro, marcadas como ilustrativas)
assets/site/map                      places.json (lugares e rotas a pé, calculados uma vez) e a imagem estática do mapa
_work/sitebuild                      ferramentas desta versão: imagens, lugares, mapa estático, peso, prints
_work/content/sources.md             todas as fontes do texto, com datas
```

## As seções (inglês no site, sem hífen nem travessão)

1. **The vision**: o conceito de casas empilhadas como ninhos, a ficha (34 andares, 143 casas, 51 affordable, 12 tipologias) e o que vem além das casas (jardim no topo, playground, comércio no térreo, Thames Path).
2. **Exterior views**: as sete vistas verificadas e dois renders oficiais. No desktop a seção fica presa e desliza para o lado; no celular é um carrossel. Clique abre o lightbox (setas, teclado, deslizar).
3. **Residences**: LOFT 4 e Bungalow 3, com parallax em camadas (foto principal, foto menor, selo) e "Fly to this home".
4. **The homes**: as doze tipologias privadas com áreas e jardins das plantas oficiais, e a planta oficial em abas (Bungalows, LOFTs inferior e superior, estúdios). Só LOFT 4 e Bungalow 3 levam a algum lugar.
5. **Affordable homes** e 6. **Accessible homes**: números e plantas oficiais (duplex affordable, layout para cadeira de rodas).
7. **Sustainability**: 70% de melhoria sobre a base, sistemas e materiais, diagrama oficial.
8. **Location**: imagem oficial, mapa ao vivo com estilo da marca, lugares com tempo a pé (aproximado), ilustrações do bairro, link para o Google Maps.
9. **Next steps**: linha do tempo do licenciamento (2014, 2024, 2025, agora).
10. **Talk to us**: tópicos do formulário oficial (abrem o cadastro, que não envia nada), e-mail, telefone e endereço da equipe de consulta (The CCP), site oficial e o processo 2025/0907.

## Movimento

- GSAP e ScrollTrigger carregam depois da página (nunca atrasam a torre). O CSS não esconde nada: os estados iniciais são aplicados pelo script e só no que ainda está abaixo da dobra. Sem JavaScript a página aparece inteira.
- `gsap.matchMedia`: desktop com parallax em camadas, títulos e parágrafos linha a linha e as vistas presas; celular com o mesmo, mais leve e sem prender; com movimento reduzido só fades.
- A transição do cartão para as seções: o cartão fica para trás e escurece enquanto a primeira seção sobe por cima. Com a página no topo (sempre que o palco abre) nada se move.
- O ScrollTrigger é recalculado quando o palco trava ou destrava a rolagem e depois que imagens e fontes chegam.

## Mapa

MapLibre GL com os tiles vetoriais e as fontes do OpenFreeMap (sem chave). O estilo está em `js/map.js`: base quase preta, ruas discretas, água azul profunda com borda suave, prédios 3D baixos, rótulos espaçados e nenhum nome com hífen. Carrega só quando a seção se aproxima; até lá (e se WebGL ou a rede falharem) fica a imagem estática do mesmo mapa. A rolagem da página nunca é capturada (Ctrl + rolagem ou dois dedos). Um clique na lista desenha a caminhada.

Refazer os dados do mapa: `python _work/sitebuild/make_places.py` (OSM e roteador a pé do OSRM). Refazer a imagem estática: `cd _work && node sitebuild/make_static_map.mjs`.

**Página do mapa (`map.html`, `css/map.css`, `js/mappage.js`).** O ícone de mapa no topo, um clique no mapa da seção (ou o botão que aparece no hover) e cada item de "Around the corner" (`map.html#place=id`, também `&mode=car`) abrem a página dedicada: 33 lugares com foto (Wikimedia Commons; créditos no "i" de atribuição do mapa, link "Photo credits", e em `assets/map/credits.html`, gerado por `_work/mapdata/make_credits.py`), filtros de categoria só com ícone (nome no hover/foco), A pé ou Carro, rotas reais pré-calculadas (OSRM, atravessando o Tâmisa só por pontes), visão Satélite (Esri World Imagery), prédios 3D, a torre marcada como coluna de luz e anéis de distância. Dados em `assets/map/places.json`, fotos em `assets/map/photos/`. Refazer: `_work/mapdata/` (`build_routes.py` rotas, `commons_candidates.py` candidatos de foto, `picks.json` escolhas, `make_data.py` gera JSON e fotos e atualiza os oito lugares da seção, `check_crossings.py` confere que toda travessia do rio é numa ponte).

## Voo e entrada (contrato com os vídeos)

`js/tracks.js` define `FLIGHT_TRACKS = { loft4: { fps, frames, cam }, bung3: {...} }`: para cada quadro do voo de ida, a caixa da janela no quadro 16:9 e a câmera sobre a imagem oficial. Durante o voo o contorno é desenhado nesse lugar a cada quadro (`requestVideoFrameCallback`, ou o tempo do vídeo), visível o voo inteiro e sumindo nos últimos 0,4 s; na volta usa o quadro N-1-i e aparece no fim. Sem trilha, vale o comportamento antigo. A entrada termina na foto da sala: `HANDOFF` é a identidade e a troca é um fade de 150 ms (`HANDOFF_FADE`).

## O que é ilustrativo

Nenhum preço, aluguel ou custo aparece (o empreendimento é build to rent e está em licenciamento). Os níveis (LOFT 4 nos 23 e 24, Bungalow 3 no 14) são posições contadas na imagem oficial e sempre aparecem como ilustrativos. Interiores, planta 3D, voos e as imagens do bairro são ilustrativos; tempos e distâncias do mapa são aproximados.

## Testar

```bash
cd _work && node e2e.mjs http://localhost:8080/ qa/site-e2e
```
Cerca de 80 verificações em 1600x900, 1920x1080, 1366x768, retina, celular (390x844), sem o pacote 3D, sem JavaScript e com movimento reduzido: recortes, hover só nas janelas disponíveis, contorno seguindo a janela no voo, palco travado, planta 3D, legendas dos cômodos, cartão mini mostrando a próxima vista, marcas de ilustrativo no celular, GSAP e ScrollTrigger, nada escondido depois da rolagem, vistas presas e lightbox, tipologias e plantas, mapa (estilo, marcadores, rota, rolagem livre), contato, nenhum hífen, preço ou aluguel e nenhum erro no console. Os prints ficam na pasta indicada.

Outras ferramentas: `node sitebuild/weight.mjs <url> <rótulo>` (peso da primeira carga), `node sitebuild/shots.mjs <url> <pasta> 1600x900 390x844` (prints de cada seção).
