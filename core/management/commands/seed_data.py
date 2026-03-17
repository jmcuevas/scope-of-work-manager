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
    ('016120', 'Building Cleaning'),

    # Division 02 - Existing Conditions
    ('022100', 'Survey'),
    ('024100', 'Demolition'),

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
    ('071000', 'Dampproofing and Waterproofing'),
    ('075000', 'Membrane Roofing'),
    ('078100', 'Applied Fireproofing'),
    ('079200', 'Joint Sealants'),

    # Division 08 - Openings
    ('081000', 'Doors and Frames'),
    ('084400', 'Storefront and Curtain Wall'),
    ('088000', 'Interior Glazing'),
    ('088700', 'Glazing Surface Films'),

    # Division 09 - Finishes
    ('092900', 'Gypsum Board Assemblies'),
    ('093000', 'Tiling'),
    ('095000', 'Ceilings'),
    ('095100', 'Acoustical Ceilings'),
    ('096000', 'Flooring'),
    ('096700', 'High Performance Coatings'),
    ('099000', 'Painting and Coating'),

    # Division 10 - Specialties
    ('101400', 'Signage'),
    ('102000', 'Interior Specialties'),

    # Division 11 - Equipment
    ('111300', 'Loading Dock Equipment'),
    ('114000', 'Foodservice Equipment'),

    # Division 12 - Furnishings
    ('122000', 'Window Treatments'),
    ('125000', 'Furniture'),

    # Division 14 - Conveying Equipment
    ('142000', 'Elevators'),

    # Division 21 - Fire Suppression
    ('211000', 'Fire Protection'),

    # Division 22 - Plumbing
    ('221000', 'Plumbing Systems'),

    # Division 23 - HVAC
    ('231000', 'HVAC Systems'),

    # Division 26 - Electrical
    ('261000', 'Electrical Systems'),

    # Division 27 - Communications
    ('271000', 'Structured Cabling'),
    ('274000', 'Audio-Visual Systems'),

    # Division 28 - Electronic Safety and Security
    ('281000', 'Security Systems'),

    # Division 31 - Earthwork
    ('312000', 'Earthwork and Grading'),

    # Division 32 - Exterior Improvements
    ('321200', 'Asphalt Paving'),
    ('321300', 'Concrete Paving'),
    ('329000', 'Landscaping and Irrigation'),

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
