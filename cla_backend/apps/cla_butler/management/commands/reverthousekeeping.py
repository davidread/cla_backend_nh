# coding=utf-8
import os

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand

from cla_butler.qs_to_file import QuerysetToFile
from cla_eventlog.models import Log
from cla_provider.models import Feedback
from complaints.models import Complaint
from diagnosis.models import DiagnosisTraversal
from legalaid.models import (
    Case,
    EligibilityCheck,
    CaseNotesHistory,
    Person,
    Income,
    Savings,
    Deductions,
    PersonalDetails,
    ThirdPartyDetails,
    AdaptationDetails,
    CaseKnowledgebaseAssignment,
    EODDetails,
    EODDetailsCategory,
    Property,
)
from timer.models import Timer


MODELS = [
    Deductions,
    Income,
    Savings,
    Person,
    AdaptationDetails,
    PersonalDetails,
    ThirdPartyDetails,
    EligibilityCheck,
    Property,
    DiagnosisTraversal,
    Case,
    EODDetails,
    EODDetailsCategory,
    Complaint,
    CaseKnowledgebaseAssignment,
    Timer,
    Feedback,
    CaseNotesHistory,
    Log,
    LogEntry,
]


class Command(BaseCommand):

    help = "Attempts to re-load data that was deleted in the housekeeping"

    def add_arguments(self, parser):
        parser.add_argument("directory", nargs=1)

    def handle(self, *args, **options):
        path = os.path.join(settings.TEMP_DIR, args[0])
        filewriter = QuerysetToFile(path)

        for model in MODELS:
            self.stdout.write(model.__name__)
            filewriter.load(model)
