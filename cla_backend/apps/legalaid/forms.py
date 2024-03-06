import datetime

from django.utils import timezone

from cla_eventlog.forms import BaseCaseLogForm
from .utils.sla import get_sla_time


class BaseCallMeBackForm(BaseCaseLogForm):
    LOG_EVENT_KEY = "call_me_back"

    def get_requires_action_at(self):
        raise NotImplementedError()

    def get_sla_base_time(self, _dt):
        return timezone.localtime(_dt)

    def get_context(self):
        requires_action_at = self.get_requires_action_at()
        _dt = self.get_sla_base_time(requires_action_at)
        return {
            "requires_action_at": _dt,
            "sla_15": get_sla_time(_dt, 15),
            "sla_30": get_sla_time(_dt, 30),
            "sla_120": get_sla_time(_dt, 120),
            "sla_480": get_sla_time(_dt, 480),
            "sla_72h": get_sla_time(_dt, 4320),
        }

    def get_notes(self):
        dt = timezone.localtime(self.get_requires_action_at())
        end = dt + datetime.timedelta(minutes=30)
        return u"Callback scheduled for {start} - {end}. {notes}".format(
            start=dt.strftime("%d/%m/%Y %H:%M"), end=end.strftime("%H:%M"), notes=self.cleaned_data["notes"] or ""
        )

    def save(self, user):
        super(BaseCallMeBackForm, self).save(user)
        dt = self.get_requires_action_at()
        self.case.set_requires_action_at(dt)
