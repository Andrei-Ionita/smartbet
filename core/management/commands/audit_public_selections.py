import json

from django.core.management.base import BaseCommand

from core.services.public_selections import audit_ledger


class Command(BaseCommand):
    help = 'Read-only integrity and settlement audit for the public selection ledger.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true', dest='as_json')

    def handle(self, *args, **options):
        report = audit_ledger()
        if options['as_json']:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        else:
            self.stdout.write(
                f"Checked {report['checked']} selections; "
                f"{report['passed']} passed; {report['issue_count']} issues."
            )
            for code, count in report['issues_by_code'].items():
                self.stdout.write(f'- {code}: {count}')
        if report['issue_count']:
            self.stderr.write(self.style.WARNING(
                'Audit found discrepancies. No rows were changed.'
            ))
