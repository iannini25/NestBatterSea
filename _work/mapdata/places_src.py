# The places of the dedicated map page: the single source the build scripts read.
# id, name, category, what it is (short line), lat, lon, coordinate source, Commons search queries,
# and the lead image of the English Wikipedia article when there is one (a first candidate).
SITE = {'id': 'nest', 'name': 'Nest Battersea', 'address': '38 Lombard Road, Battersea, London SW11 3RP',
        'lat': 51.469488, 'lon': -0.1782451, 'osm': 'way/306984713 (Heliport House, SW11 3RP)'}

CATS = [
    ('river', 'Riverside'),
    ('transport', 'Transport'),
    ('parks', 'Parks'),
    ('food', 'Food and shops'),
    ('culture', 'Culture and sport'),
    ('everyday', 'Schools and health'),
]

P = [
  # ---- riverside and bridges
  dict(id='path', name='Thames Path', cat='river', kind='The riverside walk passes the door', lat=51.470765, lon=-0.178441, src='osm way/108957271',
       q=['Thames Path Battersea', 'Thames Path Battersea Reach', 'Battersea riverside walk'], lead=None, door=True),
  dict(id='heliport', name='London Heliport', cat='river', kind='The heliport next door, on the river', lat=51.470000, lon=-0.179444, src='wikipedia',
       q=['London Heliport Battersea', 'Battersea heliport'], lead='London_Heliport_-_Battersea_-_London_-_2_helicopters_awaiting_takeoff_-_evening_-_030604.jpg'),
  dict(id='stmarys', name="St Mary's Battersea", cat='river', kind='Georgian church on the riverbank', lat=51.476548, lon=-0.175429, src='osm way/206237163',
       q=["St Mary's Church Battersea", "St Mary Battersea church river"], lead='Church_of_Saint_Mary,_Battersea_(West_Face_-_01).jpg'),
  dict(id='chelsea', name='Chelsea Harbour', cat='river', kind='Marina and riverside, across the water', lat=51.474058, lon=-0.179741, src='osm node/1141549036',
       q=['Chelsea Harbour marina', 'Chelsea Harbour London'], lead='Chelsea_Harbour_-_geograph.org.uk_-_1526537.jpg'),
  dict(id='battbridge', name='Battersea Bridge', cat='river', kind='Road and foot bridge to Chelsea', lat=51.481111, lon=-0.1725, src='wikipedia',
       q=['Battersea Bridge London', 'Battersea Bridge Thames'], lead='Battersea_bridge_1.jpg'),
  dict(id='albert', name='Albert Bridge', cat='river', kind='The lit Victorian bridge to Chelsea', lat=51.4823, lon=-0.1667, src='wikipedia',
       q=['Albert Bridge London night', 'Albert Bridge London'], lead='Albert_Bridge_from_Chelsea_Embankment.jpg'),
  dict(id='wandbridge', name='Wandsworth Bridge', cat='river', kind='Road and foot bridge to Fulham', lat=51.464877, lon=-0.187725, src='osm way/376243939',
       q=['Wandsworth Bridge', 'Wandsworth Bridge Thames'], lead='Wandsworth_Bridge.JPG'),

  # ---- transport
  dict(id='pier', name="St Mary's Wandsworth Pier", cat='transport', kind='River bus, Uber Boat by Thames Clippers', lat=51.467055, lon=-0.182466, src='osm node/3846551161',
       q=['Plantation Wharf Pier', 'Wandsworth Riverside Quarter Pier', 'Thames Clipper Battersea', 'Uber Boat Thames Clippers'], lead=None),
  dict(id='clapham', name='Clapham Junction', cat='transport', kind='National Rail and London Overground', lat=51.464459, lon=-0.170518, src='osm node/5735001231',
       q=['Clapham Junction station', 'Clapham Junction railway station entrance'], lead='Clapham_Junction_Railway_Station_South_Western_Entrance.jpg'),
  dict(id='imperial', name='Imperial Wharf', cat='transport', kind='London Overground, across the river', lat=51.475103, lon=-0.182927, src='osm',
       q=['Imperial Wharf station'], lead='Imperial_Wharf_stn_western_entrance2.JPG'),
  dict(id='wandtown', name='Wandsworth Town', cat='transport', kind='National Rail to Waterloo', lat=51.4609, lon=-0.1879, src='wikipedia',
       q=['Wandsworth Town station', 'Wandsworth Town railway station'], lead='Wandsworth_Town_Station_Platform.jpg'),
  dict(id='bpstation', name='Battersea Power Station station', cat='transport', kind='Northern line, London Underground', lat=51.479872, lon=-0.142507, src='osm way/925859532',
       q=['Battersea Power Station tube station', 'Battersea Power Station Underground station entrance'], lead='Battersea_Power_Station_48.jpg'),
  dict(id='bparkstn', name='Battersea Park station', cat='transport', kind='National Rail to Victoria', lat=51.4779, lon=-0.1477, src='wikipedia',
       q=['Battersea Park railway station'], lead='2018_at_Battersea_Park_station_-_facade.JPG'),
  dict(id='fulham', name='Fulham Broadway', cat='transport', kind='District line, across the river', lat=51.480126, lon=-0.194547, src='osm node/469760147',
       q=['Fulham Broadway station', 'Fulham Broadway tube station'], lead='FulhamBroadway1.jpg'),

  # ---- parks
  dict(id='lake', name='Battersea Park', cat='parks', kind='The boating lake and gardens', lat=51.478398, lon=-0.15412, src='osm relation/1115029',
       q=['Battersea Park boating lake', 'Battersea Park lake'], lead=None),
  dict(id='pagoda', name='Peace Pagoda', cat='parks', kind='On the river in Battersea Park', lat=51.482017, lon=-0.159060, src='osm way/33887712',
       q=['Peace Pagoda Battersea Park', 'Battersea Park Pagoda'], lead='Southwest_View_of_the_Battersea_Park_Pagoda_(02).jpg'),
  dict(id='zoo', name="Children's Zoo", cat='parks', kind='Battersea Park Children’s Zoo', lat=51.481185, lon=-0.156566, src='osm way/60693939',
       q=["Battersea Park Children's Zoo", 'Battersea Park Zoo'], lead=None),
  dict(id='york', name='York Gardens', cat='parks', kind='Neighbourhood park and playground', lat=51.467329, lon=-0.176956, src='osm way/4416384',
       q=['York Gardens Battersea', 'York Gardens library Battersea'], lead=None),
  dict(id='claphamc', name='Clapham Common', cat='parks', kind='Open common, ponds and bandstand', lat=51.4578, lon=-0.1494, src='wikipedia',
       q=['Clapham Common bandstand', 'Clapham Common'], lead=None),
  dict(id='wandc', name='Wandsworth Common', cat='parks', kind='Common land, lakes and woods', lat=51.448464, lon=-0.167588, src='osm relation/2841550',
       q=['Wandsworth Common lake', 'Wandsworth Common'], lead=None),
  dict(id='physic', name='Chelsea Physic Garden', cat='parks', kind='Walled botanic garden of 1673', lat=51.48457, lon=-0.162262, src='osm way/10806964',
       q=['Chelsea Physic Garden'], lead='II_Chelsea_Physic_Garden,_London,_UK.jpg'),

  # ---- food and shops
  dict(id='batsq', name='Battersea Square', cat='food', kind='Restaurants and cafés by the river', lat=51.474978, lon=-0.175332, src='osm way/4719940',
       q=['Battersea Square', 'Battersea Square London'], lead=None),
  dict(id='northcote', name='Northcote Road', cat='food', kind='Independent shops, cafés and market', lat=51.4605, lon=-0.1665, src='osm way/4348721',
       q=['Northcote Road Battersea', 'Northcote Road market'], lead='Northcote_Road_SW11_(4)_-_geograph.org.uk_-_187108.jpg'),
  dict(id='power', name='Battersea Power Station', cat='food', kind='Shops, restaurants and the chimney lift', lat=51.481775, lon=-0.144552, src='osm',
       q=['Battersea Power Station 2023', 'Battersea Power Station redevelopment'], lead='Battersea_Power_Station_from_the_river.jpg'),
  dict(id='kings', name="King's Road", cat='food', kind='Chelsea shopping street', lat=51.48737, lon=-0.168874, src='wikipedia',
       q=["King's Road Chelsea", 'Kings Road Chelsea shops'], lead='Kings_Road_SW3.jpg'),
  dict(id='ship', name='The Ship', cat='food', kind='Riverside pub at Wandsworth', lat=51.463573, lon=-0.188181, src='osm way/331995902',
       q=['The Ship Wandsworth', 'The Ship pub Jews Row'], lead=None),
  dict(id='southside', name='Southside Wandsworth', cat='food', kind='Shopping centre and cinema', lat=51.454722, lon=-0.193611, src='wikipedia',
       q=['Southside Wandsworth', 'Southside shopping centre Wandsworth'], lead='Southside_Wandsworth_interior_view_of_Central_Mall.JPG'),
  dict(id='stjohns', name="St John's Hill", cat='food', kind='High street by Clapham Junction', lat=51.4622, lon=-0.1735, src='osm',
       q=["St John's Road Clapham Junction", 'St Johns Road Battersea'], lead=None),

  # ---- culture and sport
  dict(id='bac', name='Battersea Arts Centre', cat='culture', kind='Theatre in the old town hall', lat=51.4648, lon=-0.1607, src='wikipedia',
       q=['Battersea Arts Centre'], lead='Battersea_Arts_Centre_09.JPG'),
  dict(id='stamford', name='Stamford Bridge', cat='culture', kind='Home of Chelsea Football Club', lat=51.481667, lon=-0.191111, src='wikipedia',
       q=['Stamford Bridge stadium', 'Stamford Bridge Chelsea'], lead='London_Stamford_Bridge.jpg'),
  dict(id='arena', name='Millennium Arena', cat='culture', kind='Running track and courts, Battersea Park', lat=51.48109, lon=-0.15162, src='osm way/25864025',
       q=['Battersea Park Millennium Arena', 'Battersea Park athletics track', 'Battersea Park tennis'], lead=None),

  # ---- schools and health
  dict(id='harris', name='Harris Academy Battersea', cat='everyday', kind='State secondary school', lat=51.473259, lon=-0.159127, src='osm way/322432645',
       q=['Harris Academy Battersea'], lead='Harris_Academy_Battersea.jpg'),
  dict(id='chelwest', name='Chelsea and Westminster', cat='everyday', kind='Hospital with A and E', lat=51.484, lon=-0.182, src='wikipedia',
       q=['Chelsea and Westminster Hospital'], lead='Chelsea_Westminster_Hospital_Front,_Fulham_Road.jpg'),
]
