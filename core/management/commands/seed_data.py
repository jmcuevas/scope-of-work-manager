from django.core.management.base import BaseCommand
from core.models import ProjectType, CSITrade


PROJECT_TYPES = [
    ('Office Tenant Improvement', 'Office TI — interior fit-out of existing office space'),
    ('Lab / R&D Tenant Improvement', 'Lab or R&D TI — specialized MEP, exhaust, and utility requirements'),
    ('Core & Shell', 'New ground-up construction delivering base building only'),
    ('Seismic Retrofit', 'Structural seismic upgrades to existing building'),
    ('Mixed-Use', 'Combined residential, retail, and/or office uses'),
    ('Other', 'Custom project type not covered by standard categories'),
]

CSI_TRADES = [
    # Division 01 - General Requirements
    ('011000', 'Summary of Work'),
    ('015000', 'Temporary Facilities and Controls'),

    # Division 02 - Existing Conditions
    ('024100', 'Demolition'),
    ('024200', 'Removal and Salvage of Construction Materials'),

    # Division 03 - Concrete
    ('033000', 'Cast-in-Place Concrete'),

    # Division 04 - Masonry
    ('042000', 'Unit Masonry'),

    # Division 05 - Metals
    ('051200', 'Structural Steel Framing'),
    ('055000', 'Metal Fabrications'),

    # Division 06 - Wood, Plastics, and Composites
    ('061000', 'Rough Carpentry'),
    ('064000', 'Architectural Woodwork'),

    # Division 07 - Thermal and Moisture Protection
    ('071000', 'Waterproofing'),
    ('075000', 'Membrane Roofing'),
    ('079000', 'Joint Sealants'),

    # Division 08 - Openings
    ('081100', 'Metal Doors and Frames'),
    ('083200', 'Sliding Aluminum-Framed Glass Doors'),
    ('084000', 'Entrances, Storefronts, and Curtain Walls'),
    ('084100', 'Entrances and Storefronts'),
    ('084400', 'Curtain Wall and Glazing'),
    ('087100', 'Door Hardware'),
    ('088000', 'Glazing'),

    # Division 09 - Finishes
    ('092100', 'Plaster and Gypsum Board'),
    ('092900', 'Gypsum Board / Drywall'),
    ('093000', 'Tiling'),
    ('095100', 'Acoustical Ceilings'),
    ('096500', 'Resilient Flooring'),
    ('096800', 'Carpet'),
    ('097000', 'Wall Coverings'),
    ('099000', 'Paints and Coatings'),

    # Division 10 - Specialties
    ('101400', 'Signage'),
    ('102800', 'Toilet, Bath, and Laundry Accessories'),
    ('104400', 'Fire Protection Specialties'),

    # Division 11 - Equipment
    ('111300', 'Loading Dock Equipment'),

    # Division 12 - Furnishings
    ('122100', 'Window Blinds'),
    ('123600', 'Countertops'),

    # Division 14 - Conveying Equipment
    ('142000', 'Elevators'),
    ('144000', 'Lifts'),

    # Division 21 - Fire Suppression
    ('210000', 'Fire Suppression'),
    ('211300', 'Fire Sprinkler'),

    # Division 22 - Plumbing
    ('220000', 'Plumbing'),
    ('224000', 'Plumbing Fixtures'),

    # Division 23 - HVAC
    ('230000', 'HVAC'),
    ('239000', 'BMS / Controls'),

    # Division 26 - Electrical
    ('260000', 'Electrical'),

    # Division 27 - Communications
    ('270000', 'Communications'),
    ('271000', 'Structured Cabling / Data & Voice'),
    ('274000', 'Audio-Visual'),

    # Division 28 - Electronic Safety and Security
    ('280000', 'Security Systems'),

    # Division 31 - Earthwork
    ('312000', 'Earthwork and Grading'),
    ('314000', 'Shoring and Underpinning'),

    # Division 32 - Exterior Improvements
    ('321200', 'Asphalt Paving'),
    ('321300', 'Concrete Paving'),
    ('329000', 'Planting / Landscaping'),

    # Division 33 - Utilities
    ('330000', 'Site Utilities'),
]


class Command(BaseCommand):
    help = 'Seed initial lookup data: ProjectTypes and CSI Trades'

    def handle(self, *args, **options):
        self._seed_project_types()
        self._seed_csi_trades()
        self.stdout.write(self.style.SUCCESS('Seed data loaded successfully.'))

    def _seed_project_types(self):
        created = 0
        for name, description in PROJECT_TYPES:
            _, was_created = ProjectType.objects.get_or_create(
                name=name,
                defaults={'description': description},
            )
            if was_created:
                created += 1
        self.stdout.write(f'  ProjectTypes: {created} created, {len(PROJECT_TYPES) - created} already existed')

    def _seed_csi_trades(self):
        created = 0
        for csi_code, name in CSI_TRADES:
            _, was_created = CSITrade.objects.get_or_create(
                csi_code=csi_code,
                defaults={'name': name},
            )
            if was_created:
                created += 1
        self.stdout.write(f'  CSI Trades: {created} created, {len(CSI_TRADES) - created} already existed')
