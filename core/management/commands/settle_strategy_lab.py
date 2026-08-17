"""Settle qualified, fixed-horizon Strategies Lab decisions."""
from django.core.management.base import BaseCommand

from core.services import strategy_lab


class Command(BaseCommand):
    help = 'Settle private Strategies Lab decisions against confirmed results.'

    def handle(self, *args, **options):
        summary = strategy_lab.settle()
        self.stdout.write(
            f"strategy decisions {summary['decisions']}: "
            f"{summary['written']} settled, {summary['skipped']} unchanged, "
            f"{summary['awaiting_result']} awaiting confirmed result"
        )
