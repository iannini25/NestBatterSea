# Nest Battersea — pasta de referências

Tudo que foi usado para construir o site, mais o levantamento do projeto real.

---

## ⚠️ O que descobrimos sobre o projeto (leia antes de apresentar)

O site oficial **nestbattersea.co.uk não é um site de vendas**. É um site de
**consulta pública de licenciamento**, feito pela consultoria The CCP para o
processo no Wandsworth Council (aplicação **2025/0907**).

**O prédio ainda não foi aprovado nem construído.**

Por isso **não existem** — e não foram inventados em lugar nenhum do site:

| Item | Situação |
|---|---|
| Preço / aluguel | Não publicado. Projeto é **build-to-rent** (aluguel), não venda |
| Número do apartamento | Não existe — as plantas são diagramáticas, por posição (01–06) |
| Andar específico | Não existe |
| Disponibilidade / vendido | Não existe |
| Vista ou orientação por unidade | Não existe |
| Medidas cômodo-a-cômodo | Não existem (só áreas totais em m²) |

O site que construímos reflete isso: ele mostra **áreas reais** e diz
explicitamente, no painel da unidade, que não há preço publicado.

---

## Ficha técnica do empreendimento (verificada)

| | |
|---|---|
| Nome | Nest Battersea |
| Endereço | 38 Lombard Road, Battersea, London SW11 3RP |
| Pavimentos | **34** |
| Altura | ~122 m (indicativo — não confirmado por fonte oficial) |
| Residências | **143** (51 affordable) |
| Arquitetos | **HTA Design LLP** + **Concrete (Amsterdam)** |
| Incorporador | **Heliport London Ltd** (grupo Canada Israel) |
| Tenure | Build to rent — todas para aluguel |
| Vagas | Car-free |
| Acessibilidade | 10% wheelchair user dwellings (Part M4(3)) |
| Vizinhança | Ao lado do London Heliport, de frente pro Tâmisa |
| Status | Em licenciamento. O comitê de patrimônio de Wandsworth se manifestou **contra** em 14/07/2025 |

### O conceito "Nest"
Não são apartamentos convencionais. São **"sky homes"**:
- **Bungalows** — casas de um pavimento, no céu
- **LOFTs / Duplexes** — casas de dois pavimentos, pé-direito duplo

Cada uma com **jardim privativo plantado**. Daí o nome: ninhos verdes agarrados
na torre. É por isso que a fachada tem varanda vegetada em todo pavimento.

### Marca
- Fonte: **Poppins** (300/400/500/600)
- Azul primário: **#92B7CA** · hover **#C9E2EF** · escuro **#5D95B1**
- Texto: **#4D4D4F** · quase-preto **#161922**

> Nota: o site oficial é claro/institucional. O nosso é escuro — decisão
> deliberada, porque é um site de **venda em cena noturna**, não de consulta
> pública. A paleta de marca foi mantida.

---

## As duas unidades do demo (ambas REAIS)

### LOFT 4 — `Private 04`
- Double height sky home (pé-direito duplo, dois pavimentos)
- **4 quartos / 7 pessoas**
- Interior **134 m²** · jardim privativo **12 m²**
- É a maior unidade privada do pavimento
- Fonte: plantas `fp-31.png` (lower) e `fp-32.png` (upper)

### Bungalow 3 — `Private 03`
- Single height sky home (um pavimento)
- **2 quartos / 3 pessoas**
- Interior **65 m²** · jardim privativo **15 m²**
- Fonte: planta `fp-33.png`

### Todas as tipologias publicadas (para referência)

**Single height — Private:** Bungalow 1 (2b3p, 61 m²) · Bungalow 2 (1b2p, 51 m²) ·
Bungalow 3 (2b3p, 65 m²) · Bungalow 4B (2b4p, 76 m²) · Bungalow 5 (2b3p, 62 m²) ·
Bungalow 6 (1b2p, 53 m²)

**Double height — Private:** LOFT 1 (3b5p, 100 m²) · LOFT 2 (2b4p, 79 m²) ·
LOFT 3 (3b6p, 112 m²) · **LOFT 4 (4b7p, 134 m²)** · LOFT 5 (3b6p, 107 m²) ·
LOFT 6 (2b4p, 86 m²)

---

## Conteúdo das pastas

### `cgi-oficial/`
CGIs e referências que você mandou + os oficiais baixados do site deles.
`01-night-river.jpg` é o CGI noturno oficial em 2560×1920 — a base de
fidelidade de tudo que foi gerado.

### `plantas-oficiais/`
As 10 plantas oficiais em resolução máxima (2000×1422), direto do
design & access statement deles:
- `fp-28` a `fp-34` — as 7 plantas de pavimento
- `aff-29`, `aff-30` — affordable, duplo pé-direito
- `wheelchair.png` — **a única planta com áreas cômodo-a-cômodo**

### `videos-referencia/`
- `video1-referencia-planta3d.mp4` — a ref da planta 3D "dollhouse" + barra de legenda
- `video2-referencia-flyin.mp4` — a ref do seletor de andar + voo até a janela

### `assets-gerados/`
Tudo que foi gerado no Higgsfield, em resolução original:
- `hero-v1.png` → `hero-4k.png` — a fachada master (4096×2294)
- `window-close.png`, `arrive-b.png` — keyframes de chegada da câmera
- `int-living/bed/bath/balcony.png` — interiores
- `fly-a.mp4`, `fly-b.mp4` — os voos de câmera originais em 2560×1440
- `chk-hi.jpg`, `chk-lo.jpg` — validação das máscaras de janela sobre a fachada

### `docs/site-html/`
O HTML cru das 10 páginas do site oficial + o CSS dinâmico (de onde saiu a paleta).

---

## Como os assets foram feitos (para refazer com outro prédio)

1. **Fachada master** — `gpt_image_2_6` com os CGIs reais como `image_references`,
   prompt descrevendo material por material, lente teleobjetiva 200mm de um drone
   na altura média da torre (isso mantém as verticais paralelas, o que é o que
   faz as máscaras de janela encaixarem). Depois upscale para 4K.

2. **Keyframe de chegada** — close da janela, gerado com a fachada como referência.

3. **O voo** — `minimax_h3` com **start_image = fachada** e **end_image = o close**.
   É isso que faz a câmera realmente ir de um ponto ao outro em vez de alucinar.
   5s, 2K, ~10 créditos cada.

4. **A volta** — `ffmpeg ... -vf reverse`. O vídeo reverso refaz o caminho exato,
   de graça. É por isso que o "voltar" funciona de verdade.

5. **A chegada sem salto** — o fundo estático da tela da unidade é o
   **último frame real do vídeo**, extraído com `ffmpeg -sseof`. Zero corte visível.

---

## Fontes

- Site oficial: https://nestbattersea.co.uk/
- Aplicação de planejamento: https://planning.wandsworth.gov.uk → **2025/0907**
- Buildington: https://www.buildington.co.uk/buildings/12102/england/london-sw11/38-lombard-road/nest-battersea
- Architects' Journal: https://www.architectsjournal.co.uk/news/hta-and-concrete-reveal-battersea-tower-plans
- Battersea Society (objeção formal): https://www.batterseasociety.org.uk/
