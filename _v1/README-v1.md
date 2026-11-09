# Nest Battersea — seletor interativo de residências

Site de demonstração. A fachada é navegável: passe o mouse nas janelas
acesas, clique, e a câmera **voa de verdade** até o apartamento.

## Rodar

```bash
cd NestBatterSea-LONDON
python3 -m http.server 8080
```
Abra `http://localhost:8080`

> Precisa de servidor. Abrir `index.html` direto do disco (`file://`)
> quebra o carregamento dos vídeos.

## Estrutura

```
index.html
css/app.css          estilos
js/data.js           ← OS DADOS DAS UNIDADES ESTÃO AQUI
js/app.js            máquina de estados + animação
assets/
  facade/            fachada master (4K/2K/1280) + frames de chegada
  video/             voos de câmera, ida e volta
  interiors/         renders internos
  plans/             plantas oficiais recortadas por unidade
_refs/               TODAS as referências + levantamento do projeto real
```

## Como funciona o voo de câmera

Não é `transform: scale()`. É render de verdade:

1. Clique → toca `flight-<unidade>.mp4`. O **primeiro frame do vídeo é
   exatamente a imagem da fachada**, então a troca é invisível.
2. O vídeo termina → mostra `arrive-<unidade>.jpg`, que é o **último frame
   real do próprio vídeo**. Zero salto.
3. "Voltar" → toca `flight-<unidade>-rev.mp4`, o mesmo render invertido.
   A câmera refaz o caminho exato de volta.

Essa é a razão de a volta parecer certa: não é uma animação nova, é o
mesmo movimento rodando ao contrário.

## As máscaras das janelas

Em `js/data.js`, cada residência tem um `poly` — um polígono de 6 pontos
no espaço de coordenadas do render master (**4096 × 2294**).

Os polígonos acompanham a perspectiva (a janela de esquina vira duas
faces inclinadas), por isso a máscara cobre **só o vidro** — não a laje,
não a varanda.

Para ajustar: edite os pontos e recarregue. O SVG escala junto com a
imagem, então os valores não mudam com o tamanho da tela.

## Trocar as unidades

Tudo em `js/data.js`. Cada objeto em `RESIDENCES` controla uma unidade
inteira: nome, áreas, polígono, vídeos, plantas e galeria.

O array `LET` são as janelas apagadas (vendidas/alugadas) — só escurecem
e mostram tooltip, não são clicáveis.

## Sobre os dados

Áreas, nomes de unidade e tipologias são **reais**, retirados da
documentação oficial do empreendimento (Wandsworth 2025/0907).

**Não há preço em lugar nenhum** porque o projeto é build-to-rent e nunca
publicou valores. O painel da unidade diz isso explicitamente.

Leia `_refs/LEIA-ME.md` antes de apresentar — tem o levantamento completo
e as ressalvas.

## Peso

~25 MB no total, sendo 21 MB os quatro vídeos. Para produção:
- sirva os vídeos por CDN
- gere versões `.webm` (VP9) — costuma cair ~40%
- considere 3s em vez de 5s nos voos
