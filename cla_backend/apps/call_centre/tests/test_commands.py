from django.test import TestCase
from django.core.management import call_command
from django.utils.six import StringIO
from core.tests.mommy_utils import make_recipe, make_user


class OrganisationOperatorCommandTest(TestCase):
    def test_create_and_assign_agilisys_organisation(self):
        organisation = make_recipe("call_centre.organisation", name="Agilisys")

        make_recipe("call_centre.operator", user=make_user(email="user1@agilisys.co.uk"))
        make_recipe("call_centre.operator", user=make_user(email="user2@Agilisys.co.uk"))
        make_recipe("call_centre.operator", user=make_user(email="user2@agilisys.co.uki"))
        make_recipe("call_centre.operator", user=make_user(email="user3@agilisys.co.uk"), organisation=organisation)
        make_recipe("call_centre.operator", user=make_user(email="user1@hgs.co.uk"))
        make_recipe("call_centre.operator", user=make_user(email="user1@yahoo.co.uk"))
        make_recipe("call_centre.operator", user=make_user(email="user1@yahoo.co.uk"))

        out = StringIO()
        call_command("create_and_assign_agilisys_organisation", stdout=out)
        self.assertIn("Updating 2 Agilisys operators...done", out.getvalue())

    def test_create_and_assign_agilisys_organisation_idempotent(self):
        make_recipe("call_centre.operator", user=make_user(email="user1@agilisys.co.uk"))
        make_recipe("call_centre.operator", user=make_user(email="user2@agilisys.co.uk"))
        out = StringIO()
        call_command("create_and_assign_agilisys_organisation", stdout=out)
        call_command("create_and_assign_agilisys_organisation", stdout=out)
        self.assertIn("Could not find Agilisys operators to update", out.getvalue())
