from django.db import models


class MatchState(models.Model):
    """The single live match. Row pk=1 is the one every device shares."""

    state = models.JSONField(null=True, blank=True)      # whole scoreboard state
    images = models.JSONField(default=dict, blank=True)  # logos / player photos (data URLs)
    version = models.PositiveIntegerField(default=0)     # +1 on every score update
    img_version = models.PositiveIntegerField(default=0) # +1 on every photo upload
    by = models.CharField(max_length=40, blank=True)     # which device wrote last
    state_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Live match (v{self.version})"
