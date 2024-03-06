from django.core.management import BaseCommand
from legalaid.models import Case
from call_centre.models import Organisation


class Command(BaseCommand):
    help = "Assign existing cases to organisation based on the organisation of the user that created the case"

    def handle(self, *args, **options):
        default_organisation = Organisation.objects.get(name="Agilisys")
        organisations = Organisation.objects.values_list("id", flat=True)

        cases_qs = Case.objects.filter(organisation__isnull=True).select_related(
            "created_by", "created_by__operator__organisation"
        )
        count = cases_qs.count()
        self.stdout.write("{count} cases found.".format(count=count))
        if not count:
            return

        self.stdout.write("Assigning organisations based on creator organisation")
        for organisation in organisations:
            qs = cases_qs.filter(created_by__operator__organisation=organisation)
            qs.update(organisation=organisation)

        # Cases created by users that do not have organisation will be assigned to the default organisation
        cases_qs.update(organisation=default_organisation)
