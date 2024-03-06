import datetime

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import ugettext_lazy as _
from django.forms.util import ErrorList
from django.utils import timezone

from cla_common.call_centre_availability import OpeningHours
from cla_common.constants import (
    GENDERS,
    ETHNICITIES,
    RELIGIONS,
    SEXUAL_ORIENTATIONS,
    DISABILITIES,
    OPERATOR_HOURS,
    CASE_SOURCE,
)

from knowledgebase.models import Article

from legalaid.utils import diversity
from legalaid.forms import BaseCallMeBackForm

from cla_eventlog import event_registry
from cla_eventlog.forms import BaseCaseLogForm, EventSpecificLogForm

from cla_provider.models import Provider
from cla_provider.helpers import notify_case_RDSPed


operator_hours = OpeningHours(**OPERATOR_HOURS)


class ProviderAllocationForm(BaseCaseLogForm):
    LOG_EVENT_KEY = "assign_to_provider"

    provider = forms.ChoiceField()
    is_manual = forms.BooleanField(required=False)
    is_manual_ref = forms.BooleanField(required=False)
    is_spor = forms.BooleanField(required=False)
    is_urgent = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.providers = kwargs.pop("providers", None)
        if self.providers:
            self.base_fields["provider"].choices = [(p.pk, p.name) for p in self.providers]
        super(ProviderAllocationForm, self).__init__(*args, **kwargs)

    def clean_provider(self):
        provider = self.cleaned_data["provider"]

        provider_obj = Provider.objects.get(pk=provider)
        self.cleaned_data["provider_obj"] = provider_obj
        return provider

    def clean(self):
        cleaned_data = super(ProviderAllocationForm, self).clean()
        nfe = []
        if not self.providers:
            nfe.append(_(u"There is no provider specified in " u"the system to handle cases of this law category."))
            del self._errors["provider"]

        if (self.case.matter_type1 and self.case.matter_type2) and (
            not self.case.matter_type1.category == self.case.matter_type2.category
        ):
            nfe.append(
                _(
                    u"Category of matter type 1: {category1} must match category of matter type 2: {category2}".format(
                        category1=self.case.matter_type1.category.name, category2=self.case.matter_type2.category.name
                    )
                )
            )

        if self.case.eligibility_check:
            case_category = self.case.eligibility_check.category
            mt1_category = self.case.matter_type1.category if self.case.matter_type1 else None
            mt2_category = self.case.matter_type2.category if self.case.matter_type2 else None
            if case_category and mt1_category and mt2_category:
                if case_category != mt1_category or case_category != mt2_category:
                    nfe.append(
                        _(
                            u"Category of Matter Types: {category1}, {category2} must match category of case: "
                            u"{case_category}".format(
                                category1=mt1_category.name,
                                category2=mt2_category.name,
                                case_category=case_category.name,
                            )
                        )
                    )

        if nfe:
            self._errors[NON_FIELD_ERRORS] = ErrorList(nfe)
        return cleaned_data

    def get_notes(self):
        return u"Assigned to {provider}. {notes}".format(
            provider=self.cleaned_data["provider_obj"].name, notes=self.cleaned_data["notes"] or ""
        )

    def get_is_manual(self):
        return self.cleaned_data["is_manual"]

    def get_is_manual_ref(self):
        return self.cleaned_data.get("is_manual_ref", False)

    def get_is_spor(self):
        return self.cleaned_data.get("is_spor", False)

    def get_is_urgent(self):
        return self.cleaned_data.get("is_urgent", False)

    def get_kwargs(self):
        kwargs = super(ProviderAllocationForm, self).get_kwargs()
        kwargs["is_manual"] = self.get_is_manual()
        kwargs["is_manual_ref"] = self.get_is_manual_ref()
        kwargs["is_spor"] = self.get_is_spor()
        return kwargs

    def get_context(self):
        provider = self.cleaned_data["provider_obj"]
        return {"provider": provider.name, "provider_id": provider.id}

    def save(self, user):
        data = self.cleaned_data

        self.case.assign_to_provider(data["provider_obj"], is_urgent=self.get_is_urgent())

        super(ProviderAllocationForm, self).save(user)
        return data["provider_obj"]


class DeferAssignmentCaseForm(BaseCaseLogForm):
    LOG_EVENT_KEY = "defer_assignment"


class DeclineHelpCaseForm(EventSpecificLogForm):
    LOG_EVENT_KEY = "decline_help"


class SuspendCaseForm(EventSpecificLogForm):
    LOG_EVENT_KEY = "suspend_case"

    def clean_event_code(self):
        code = self.cleaned_data.get("event_code")
        if code:
            if code == "RDSP":
                # check that the case has really been assigned to a specialist
                if not self.case.provider:
                    raise ValidationError("You can only use RDSP if the case is assigned to a specialist")

            if code == "SAME":
                # check that the client has really received alternative help
                event = event_registry.get_event("alternative_help")
                if not self.case.log_set.filter(code__in=event.codes.keys()).count():
                    raise ValidationError("You can only use SAME if the client has received alternative help")
        return code

    def save_event(self, user):
        super(SuspendCaseForm, self).save_event(user)

        code = self.cleaned_data.get("event_code")
        if code == "RDSP":
            notify_case_RDSPed(self.case.provider, self.case)


class AlternativeHelpForm(EventSpecificLogForm):

    selected_providers = forms.ModelMultipleChoiceField(queryset=Article.objects.all(), required=False)

    LOG_EVENT_KEY = "alternative_help"

    def get_notes(self):
        notes = self.cleaned_data.get("notes")
        providers = self.cleaned_data.get("selected_providers", [])

        notes_l = [notes, "Assigned alternative help:"]
        for provider in providers:
            notes_l.append(unicode(provider))

        return "\n".join(notes_l)

    def get_event_code(self):
        code = self.cleaned_data["event_code"]

        category = self.case.diagnosis.category.code if self.case.diagnosis and self.case.diagnosis.category else None

        if code == "COSPF":
            if category in ("family", "housing"):
                code = "SPFN"
            if category in ("debt", "education", "discrimination"):
                code = "SPFM"
        return code

    def save(self, user):
        providers = self.cleaned_data.get("selected_providers", [])

        self.case.assign_alternative_help(user, providers)
        return super(AlternativeHelpForm, self).save(user)


class CallMeBackForm(BaseCallMeBackForm):

    # format "2013-12-29 23:59" always in UTC
    datetime = forms.DateTimeField()
    priority_callback = forms.BooleanField(required=False)

    def get_sla_base_time(self, _dt):
        if self.case.source in [CASE_SOURCE.SMS, CASE_SOURCE.VOICEMAIL]:
            created = self.case.created
            if timezone.is_naive(created):
                created = timezone.make_aware(created, timezone.get_default_timezone())
            return timezone.localtime(created)
        else:
            return super(CallMeBackForm, self).get_sla_base_time(_dt)

    def _is_dt_too_soon(self, dt):
        return dt <= timezone.now() - datetime.timedelta(minutes=30)

    def _is_dt_out_of_hours(self, dt):
        _dt = dt
        if timezone.is_naive(_dt):
            _dt = timezone.make_aware(_dt, timezone.utc)
        _dt = timezone.localtime(_dt)
        return _dt not in operator_hours

    def get_kwargs(self):
        kwargs = super(CallMeBackForm, self).get_kwargs()
        kwargs["priority_callback"] = self.get_priority_callback()
        return kwargs

    def clean_datetime(self):
        dt = self.cleaned_data["datetime"]
        dt = dt.replace(tzinfo=timezone.utc)

        if self._is_dt_too_soon(dt):
            raise ValidationError("Specify a date not in the current half hour.")

        if self._is_dt_out_of_hours(dt):
            raise ValidationError("Specify a date within working hours.")
        return dt

    def clean(self):
        """
        Catches further validation errors before the save.
        """
        cleaned_data = super(CallMeBackForm, self).clean()

        if self._errors:  # if already in error => skip
            return cleaned_data

        event = event_registry.get_event(self.get_event_key())()
        try:
            event.get_log_code(case=self.case, **self.get_kwargs())
        except ValueError as e:
            self._errors[NON_FIELD_ERRORS] = ErrorList([str(e)])
        return cleaned_data

    def get_requires_action_at(self):
        return self.cleaned_data["datetime"]

    def get_priority_callback(self):
        return self.cleaned_data.get("priority_callback", False)


class StopCallMeBackForm(BaseCaseLogForm):
    LOG_EVENT_KEY = "stop_call_me_back"

    action = forms.ChoiceField(choices=(("cancel", "Cancel"), ("complete", "complete")))

    def get_kwargs(self):
        action = self.cleaned_data["action"]

        kwargs = {action: True}
        return kwargs

    def clean(self):
        """
        Catches further validation errors before the save.
        """
        cleaned_data = super(StopCallMeBackForm, self).clean()

        if self._errors:  # if already in error => skip
            return cleaned_data

        event = event_registry.get_event(self.get_event_key())()
        try:
            event.get_log_code(case=self.case, **self.get_kwargs())
        except ValueError as e:
            self._errors[NON_FIELD_ERRORS] = ErrorList([str(e)])
        return cleaned_data

    def save(self, user):
        super(StopCallMeBackForm, self).save(user)
        self.case.reset_requires_action_at()


class DiversityForm(forms.Form):
    gender = forms.ChoiceField(required=True, choices=GENDERS.CHOICES)
    ethnicity = forms.ChoiceField(required=True, choices=ETHNICITIES.CHOICES)
    religion = forms.ChoiceField(required=True, choices=RELIGIONS.CHOICES)
    sexual_orientation = forms.ChoiceField(required=True, choices=SEXUAL_ORIENTATIONS.CHOICES)
    disability = forms.ChoiceField(required=True, choices=DISABILITIES.CHOICES)

    def __init__(self, *args, **kwargs):
        self.personal_details = kwargs.pop("obj")
        super(DiversityForm, self).__init__(*args, **kwargs)

    def save(self, user):
        diversity.save_diversity_data(self.personal_details.pk, self.cleaned_data)
