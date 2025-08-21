from django.contrib.gis.db import models


class FuelStation(models.Model):
    opis_truckstop_id = models.CharField(max_length=100, unique=True)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.CharField(max_length=50)
    retail_price = models.DecimalField(max_digits=5, decimal_places=3)
    location = models.PointField(geography=True, null=True, blank=True)

    def __str__(self):
        return f"{self.truckstop_name} - {self.city}, {self.state}"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None

    class Meta:
        indexes = [
            models.Index(
                fields=["location"],
                name="fuelstation_location_gist",
                opclasses=["gist"],
            )
        ]
