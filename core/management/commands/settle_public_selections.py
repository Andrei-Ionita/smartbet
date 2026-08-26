from django.core.management.base import BaseCommand

from core.services import public_selections


class Command(BaseCommand):
    help = 'Settle frozen homepage and strategy selections from confirmed results.'

    def handle(self, *args, **options):
        summary = public_selections.settle_public_selections()
        self.stdout.write(
            f"public selections: {summary['settled']} settled, "
            f"{summary['pending']} still pending"
        )
