from django.core.management.base import BaseCommand, CommandError

from core.services import public_selections


class Command(BaseCommand):
    help = ('Freeze the current homepage and named-strategy selections into '
            'the append-only public Results record.')

    def handle(self, *args, **options):
        summary = public_selections.publish_current_selections()
        portfolio = summary['portfolio']
        if portfolio['status'] != 'ok':
            raise CommandError('No fresh selection input. Run capture_signal_evidence before publication.')
        self.stdout.write(
            'public selections: '
            f"portfolio +{portfolio['published']}; "
            f"{portfolio['markets']} market selections, {portfolio['homepage']} homepage selections"
        )
