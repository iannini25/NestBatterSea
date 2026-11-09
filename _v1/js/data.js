/* ============================================================
   NEST BATTERSEA — residence data
   ------------------------------------------------------------
   SOURCE OF TRUTH
   Every area, unit name, typology and occupancy figure below is
   taken verbatim from the Nest Battersea design & access
   documentation published at nestbattersea.co.uk (Wandsworth
   planning application 2025/0907):
     · fp-31/32  "Double height sky homes - Private"  -> LOFT 4
     · fp-33     "Single height sky homes - Private"  -> Bungalow 3

   NOT PUBLISHED by the developer, therefore NOT stated as fact
   anywhere in this interface:
     · prices          (the scheme is build-to-rent, not for sale)
     · apartment numbers, floor levels, availability
     · room-by-room dimensions
   Where this demo needs such a value it is rendered with the
   `illustrative:true` flag, which prints a visible disclaimer.
   ============================================================ */

const TOWER = {
  name:      'Nest Battersea',
  address:   '38 Lombard Road, Battersea, London SW11 3RP',
  storeys:   34,
  homes:     143,
  architect: 'HTA Design LLP with Concrete, Amsterdam',
  developer: 'Heliport London Ltd',
  tenure:    'Build to rent',
  status:    'In planning — Wandsworth 2025/0907'
};

/* Hotspot polygons are in the coordinate space of the 4096x2294
   master facade render. They trace the glazed opening only —
   not the floor slab, not the balcony. */
const RESIDENCES = [
  {
    id:        'loft4',
    name:      'LOFT 4',
    ref:       'Private 04',
    type:      'Double height sky home',
    tier:      'Upper tier',
    beds:      '4 bedroom · 7 person',
    interior:  '134 m²',
    exterior:  '12 m²',
    status:    'available',
    poly:      [[1876,673],[1954,684],[2050,669],[2050,724],[1954,739],[1876,728]],
    flight:    'assets/video/flight-loft4.mp4',
    flightRev: 'assets/video/flight-loft4-rev.mp4',
    arrive:    'assets/facade/arrive-loft4.jpg',
    plans: [
      { label:'Lower floor', src:'assets/plans/loft4-lower.png' },
      { label:'Upper floor', src:'assets/plans/loft4-upper.png' }
    ],
    shots: [
      { t:'Living & Kitchen', src:'assets/interiors/living.jpg'   },
      { t:'Principal Bedroom', src:'assets/interiors/bedroom.jpg'  },
      { t:'Principal Bathroom', src:'assets/interiors/bathroom.jpg' },
      { t:'The Garden',        src:'assets/interiors/balcony.jpg'  }
    ],
    specs: [
      ['Typology',       'Double height'],
      ['Occupancy',      '4 bed / 7 person'],
      ['Interior',       '134 m²', '1,442 sq ft'],
      ['Private garden', '12 m²',  '129 sq ft'],
      ['Ceilings',       'Full double height']
    ]
  },
  {
    id:        'bung3',
    name:      'Bungalow 3',
    ref:       'Private 03',
    type:      'Single height sky home',
    tier:      'Mid tier',
    beds:      '2 bedroom · 3 person',
    interior:  '65 m²',
    exterior:  '15 m²',
    status:    'available',
    poly:      [[1870,1306],[1960,1311],[2045,1304],[2045,1339],[1960,1352],[1870,1345]],
    flight:    'assets/video/flight-bung3.mp4',
    flightRev: 'assets/video/flight-bung3-rev.mp4',
    arrive:    'assets/facade/arrive-bung3.jpg',
    plans: [
      { label:'Floor plan', src:'assets/plans/bungalow3.png' }
    ],
    shots: [
      { t:'Living & Kitchen', src:'assets/interiors/living.jpg'   },
      { t:'The Garden',       src:'assets/interiors/balcony.jpg'  },
      { t:'Bedroom',          src:'assets/interiors/bedroom.jpg'  },
      { t:'Bathroom',         src:'assets/interiors/bathroom.jpg' }
    ],
    specs: [
      ['Typology',       'Single height'],
      ['Occupancy',      '2 bed / 3 person'],
      ['Interior',       '65 m²', '700 sq ft'],
      ['Private garden', '15 m²', '161 sq ft'],
      ['Aspect',         'Corner, river side']
    ]
  }
];

/* Windows shown as already let. Purely to demonstrate the
   lit / unlit state logic — no occupancy data is published. */
const LET = [
  { name:'Bungalow 5', poly:[[1876,793],[1954,804],[2050,789],[2050,844],[1954,859],[1876,848]] },
  { name:'LOFT 2',     poly:[[1872,1070],[1958,1078],[2047,1066],[2047,1104],[1958,1118],[1872,1110]] },
  { name:'Bungalow 1', poly:[[1874,948],[1956,958],[2048,944],[2048,988],[1956,1003],[1874,993]] }
];

const FINE = 'Nest Battersea is a build-to-rent scheme currently in planning. ' +
             'No rent or price has been published; none is shown here. ' +
             'Areas are as stated in the published design documentation.';
