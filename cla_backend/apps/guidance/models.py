# coding=utf-8
from django.db import models

from model_utils.models import TimeStampedModel
from djorm_pgfulltext.fields import VectorField
from djorm_pgfulltext.models import SearchManager


class Tag(models.Model):
    title = models.CharField(max_length=100)

    class Meta(object):
        ordering = ("title",)

    def __unicode__(self):
        return self.title


class NoteTagRelation(models.Model):
    tag = models.ForeignKey("Tag")
    note = models.ForeignKey("Note")

    class Meta(object):
        unique_together = (("tag", "note"),)
        verbose_name = "Tag"

    def __unicode__(self):
        return u"%s (%s)" % (self.tag.title, self.note.title)


class Note(TimeStampedModel):
    title = models.CharField(max_length=100)
    body = models.TextField()
    raw_body = models.TextField()
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag", related_name="notes", through="NoteTagRelation")

    search_index = VectorField()

    objects = SearchManager(
        fields=(("title", "A"), ("tags__title", "B"), ("raw_body", "D")), auto_update_search_field=True
    )

    def __unicode__(self):
        return self.title
