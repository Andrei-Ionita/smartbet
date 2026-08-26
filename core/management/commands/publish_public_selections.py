from django.core.management.base import BaseCommand

from core.services import public_selections


class Command(BaseCommand):
    help = ('Freeze the current homepage and named-strategy selections into '
            'the append-only public Results record.')

    def handle(self, *args, **options):
        summary = public_selections.publish_current_selections()
        home = summary['homepage']
        strategies = summary['strategies']
        self.stdout.write(
            'public selections: '
            f"homepage +{home['published']} ({home['active']} active, "
            f"{home['invalid']} invalid); strategies +{strategies['published']} "
            f"({strategies['already']} already, {strategies['invalid']} invalid)"
        )
