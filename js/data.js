/* ============================================================
   NEST BATTERSEA | residence data
   ------------------------------------------------------------
   SOURCE OF TRUTH
   Typologies, areas and occupancy are verbatim from the Nest
   Battersea design and access documentation (Wandsworth planning
   application 2025/0907):
     fp-31 / fp-32  Double height sky homes, Private  (LOFT 4)
     fp-33          Single height sky homes, Private  (Bungalow 3)

   The facade is the official CGI (01-night-river.jpg). Each home's
   window is the glazed bay traced on the official render
   (tower-night.png) and mapped onto the facade image; the flight
   videos were generated from that same image to that same bay.

   NOT PUBLISHED, therefore never stated as fact here:
     prices or rents (the scheme is build to rent), apartment
     numbers, the floor of any specific home, availability,
     room by room sizes. Levels below are illustrative positions
     counted on the official render.
   ============================================================ */

const MASTER = { w: 2560, h: 1440 };          // facade image, px

const RESIDENCES = [
  {
    id: 'loft4',
    cardPhoto: 'loft4-living-2',               // residence card, a room photograph
    name: 'LOFT 4',
    ref: 'Private 04',
    type: 'Double height sky home',
    beds: 4, persons: 7,
    interior: 134, garden: 12,
    levels: 'Levels 23 and 24',
    levelNo: '23',
    window: [1244.3, 534.4, 1293.7, 578.7],   // glazed bay on the facade image
    poly: [[1241.8, 533.2], [1292.4, 532.2], [1292.4, 579.1], [1241.8, 580.0]],   // the bay as it is at the end of the flight (the outline follows it exactly)
    flight: 'loft4-flight',
    inside: 'loft4-inside',
    plans: [
      { label: 'Lower floor', src: 'assets/plans/loft4-lower.png' },
      { label: 'Upper floor', src: 'assets/plans/loft4-upper.png' }
    ],
    planNote: 'Two storeys. The living room and the garden are double height; the upper floor looks down into the living room.',
    specs: [
      ['Typology', 'Double height, two storeys'],
      ['Occupancy', '4 bedrooms · 7 people'],
      ['Interior', '134 m²', '1,442 sq ft'],
      ['Private garden', '12 m²', '129 sq ft'],
      ['Ceilings', 'Double height living']
    ]
  },
  {
    id: 'bung3',
    cardPhoto: 'bung3-terrace',
    name: 'Bungalow 3',
    ref: 'Private 03',
    type: 'Single height sky home',
    beds: 2, persons: 3,
    interior: 65, garden: 15,
    levels: 'Level 14',
    levelNo: '14',
    window: [1352, 806, 1406, 837],             // receding right face, near the north corner
    poly: [[1352, 806], [1406, 818], [1406, 837], [1352, 825]],   // the slab slopes there
    flight: 'bung3-flight',
    inside: 'bung3-inside',
    plans: [
      { label: 'Floor plan', src: 'assets/plans/bungalow3.png' }
    ],
    planNote: 'One storey. The largest garden of the bungalows wraps the living room.',
    specs: [
      ['Typology', 'Single height, one storey'],
      ['Occupancy', '2 bedrooms · 3 people'],
      ['Interior', '65 m²', '700 sq ft'],
      ['Private garden', '15 m²', '161 sq ft'],
      ['Garden', 'Largest of the bungalows']
    ]
  }
];

/* ---------- rooms with a photograph (floor plan and tour) ----------
   One entry per clickable room of the 3D plan, in tour order.
   photo = id of assets/interiors/<photo>.jpg (1920x1080); the 3D plan names its rooms by it
   level = index into the plan levels (LOFT 4: 0 lower, 1 upper)
   cap, sub = what the photograph shows (the tour caption); default: the room name and its level
   open = the photograph a click on the room opens, when the first one looks into the next room
   more = extra views of the same room, each with its own cap and sub
   view = true for photographs taken outside (the alt says "illustrative view", not "interior")  */
const ROOMS = {
  loft4: [
    // loft4-living stays first: Step inside ends on it (it is the clip's last frame). It looks in
    // from the glass wall to the dining table and the kitchen under the gallery.
    { photo: 'loft4-living', name: 'Living room', level: 0, cap: 'Dining and kitchen', sub: 'Under the gallery', open: 'loft4-living-2',
      more: [{ photo: 'loft4-living-2', cap: 'Living room', sub: 'The two storey glass wall' }] },
    { photo: 'loft4-kitchen', name: 'Kitchen and dining', level: 0, cap: 'Living room and garden', sub: 'From the dining table', open: 'loft4-kitchen-2',
      more: [{ photo: 'loft4-kitchen-2', cap: 'Kitchen', sub: 'The oak kitchen and its island' }] },
    { photo: 'loft4-hall', name: 'Entrance hall', level: 0 },
    { photo: 'loft4-bed1', name: 'Bedroom one', level: 0 },
    { photo: 'loft4-gallery', name: 'Gallery landing', level: 1, sub: 'Looking down into the living room' },
    { photo: 'loft4-bed2', name: 'Bedroom two', level: 1 },
    { photo: 'loft4-bed3', name: 'Bedroom three', level: 1 },
    { photo: 'loft4-bed4', name: 'Principal bedroom', level: 1, more: [{ photo: 'loft4-bed4-2', sub: 'Towards the window' }] },
    { photo: 'loft4-bath', name: 'Bathroom', level: 1 }
  ],
  bung3: [
    { photo: 'bung3-living', name: 'Living and dining', level: 0, cap: 'Living room', more: [{ photo: 'bung3-living-2', cap: 'Living and dining', sub: 'Towards the garden' }] },
    { photo: 'bung3-kitchen', name: 'Kitchen', level: 0 },
    { photo: 'bung3-bed1', name: 'Principal bedroom', level: 0 },
    { photo: 'bung3-bed2', name: 'Bedroom two', level: 0 },
    { photo: 'bung3-ensuite', name: 'Bathroom', level: 0 },
    { photo: 'bung3-garden', name: 'Private garden', level: 0, view: true, sub: 'Out to the river', more: [{ photo: 'bung3-terrace', sub: 'From the garden, looking in', view: true }] }
  ]
};
const LEVEL_NAMES = { loft4: ['Lower floor', 'Upper floor'], bung3: ['Single storey'] };

/* Stand in shown if a room photograph ever fails to load
   (the site asks for .avif, .webp or .jpg and falls back to this one). */
const PHOTO_STANDIN = {
  'loft4-living': 'assets/interiors/loft4-living.jpg',
  'loft4-kitchen': 'assets/stills/loft4-inside-last.jpg',
  'loft4-gallery': 'assets/stills/loft4-inside-last.jpg',
  'loft4-bed1': 'assets/interiors/loft4-bedroom.jpg',
  'loft4-bed2': 'assets/interiors/loft4-bedroom.jpg',
  'loft4-bed3': 'assets/interiors/loft4-bedroom.jpg',
  'loft4-bed4': 'assets/interiors/loft4-bedroom.jpg',
  'loft4-bath': 'assets/interiors/loft4-bathroom.jpg',
  'bung3-living': 'assets/interiors/b3-living.jpg',
  'bung3-kitchen': 'assets/stills/bung3-inside-last.jpg',
  'bung3-bed1': 'assets/interiors/b3-bedroom.jpg',
  'bung3-bed2': 'assets/interiors/b3-bedroom.jpg',
  'bung3-ensuite': 'assets/interiors/b3-bathroom.jpg',
  'bung3-garden': 'assets/interiors/b3-garden.jpg'
};

/* Clips that also exist in AV1, next to the H.264 files and named <file>-av1.mp4
   (loft4-flight-av1.mp4, loft4-flight-rev-av1.mp4, loft4-flight-720-av1.mp4,
   loft4-flight-rev-720-av1.mp4). Browsers that answer "probably" for AV1 get
   those; everyone else gets H.264. Use true once every clip has its copies. */
const VIDEO_AV1 = true;

/* Step inside: the walk in clip ends exactly on the living room photograph (its last frame is
   the photograph itself), so the hand over is the identity and a straight swap: no crossfade. */
const HANDOFF = { loft4: { x: 0, y: 0, s: 1 }, bung3: { x: 0, y: 0, s: 1 } };
const HANDOFF_FADE = 0;

RESIDENCES.forEach(r => {
  r.rooms = ROOMS[r.id];
  r.handoff = HANDOFF[r.id];
  r.levelNames = LEVEL_NAMES[r.id];
  r.thumb = `assets/site/thumb-${r.id}`;        // .webp + .jpg, mini card
  RESIDENCES[r.id] = r;                         // RESIDENCES.loft4.rooms works too
});

const BUILDING = [
  ['Address', '38 Lombard Road, Battersea, London SW11 3RP'],
  ['Storeys', '34'],
  ['Homes', '143, of which 51 affordable'],
  ['Architects', 'Concrete, Amsterdam, with HTA Design LLP'],
  ['Developer', 'Heliport London Ltd'],
  ['Tenure', 'Build to rent'],
  ['Status', 'In planning, not built (Wandsworth 2025/0907)'],
  ['Parking', 'Car free']
];

/* The twelve private typologies, verbatim from the official diagrammatic plans fp-33
   (single height) and fp-31 / fp-32 (double height): position, then for the Bungalow and
   the LOFT of that position: name, bedrooms, people, interior m², exterior (garden) m².
   The Homes section of index.html prints the same table. */
const TYPOLOGIES = [
  ['01', 'Bungalow 1', 2, 3, 61, 10, 'LOFT 1', 3, 5, 100, 10],
  ['02', 'Bungalow 2', 1, 2, 51, 9, 'LOFT 2', 2, 4, 79, 9],
  ['03', 'Bungalow 3', 2, 3, 65, 15, 'LOFT 3', 3, 6, 112, 15],
  ['04', 'Bungalow 4B', 2, 4, 76, 12, 'LOFT 4', 4, 7, 134, 12],
  ['05', 'Bungalow 5', 2, 3, 62, 14, 'LOFT 5', 3, 6, 107, 14],
  ['06', 'Bungalow 6', 1, 2, 53, 10, 'LOFT 6', 2, 4, 86, 10]
];

const FINE = 'Nest Battersea is a build to rent scheme, currently in planning. ' +
  'Areas are as stated in the published design documentation; levels are illustrative ' +
  'positions and interiors are illustrative renders.';
