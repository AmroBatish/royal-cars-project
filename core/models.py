from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.conf import settings


# =====================
# Custom User Model
# =====================
class User(AbstractUser):
    class Roles(models.TextChoices):
        USER = "user", "User"
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.USER)
    phone = models.CharField(max_length=32, blank=True)
    company_name = models.CharField(max_length=160, blank=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == self.Roles.OWNER

    @property
    def is_admin(self):
        return self.role == self.Roles.ADMIN


# =====================
# Car Model
# =====================
class Car(models.Model):
    TRANSMISSION_CHOICES = [
        ("AUTO", "Automatic"),
        ("MANUAL", "Manual"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cars",
        limit_choices_to={"role": "owner"},
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    mileage = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="cars/", blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.year})"

    class Meta:
        ordering = ["-year", "name"]


# =====================
# Booking Model
# =====================
class Booking(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_PAID = "paid"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_PAID, "Paid"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="bookings",
        null=True,
        blank=True,
    )
    pickup_location = models.CharField(max_length=200)
    drop_location = models.CharField(max_length=200)
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    return_date = models.DateField()
    return_time = models.TimeField()
    special_request = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Booking #{self.pk} - {self.user} → {self.car}"

    class Meta:
        ordering = ["-created_at"]
# =====================
# Review Model
# =====================
class Review(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, related_name="review"
    )
    car = models.ForeignKey(
        Car, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveIntegerField(default=5)  # من 1 إلى 5 مثلاً
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user} on {self.car}"

    class Meta:
        ordering = ["-created_at"]


# =====================
# Agronomist Profile
# =====================
class AgronomistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="agronomist_profile")
    specialization = models.CharField(max_length=120, blank=True)
    license_no = models.CharField(max_length=64, blank=True)
    years_experience = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(80)])
    rating_avg = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    def __str__(self):
        return f"Agronomist: {self.user.username}"


# =====================
# Owner Profile
# =====================
class OwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="owner_profile")
    company_name = models.CharField(max_length=160, blank=True)
    tax_no = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"Owner: {self.user.username}"


# =====================
# Farm Model
# =====================
class Farm(models.Model):
    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=120)
    location_text = models.CharField(max_length=255, blank=True)
    area_ha = models.DecimalField("Area (ha)", max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=16, default="active")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


# =====================
# Crop Model
# =====================
class Crop(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="crops")
    type = models.CharField(max_length=120)
    variety = models.CharField(max_length=120, blank=True)
    season_code = models.CharField(max_length=32, blank=True)
    area_ha = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    planting_date = models.DateField(blank=True, null=True)
    actual_harvest_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=16, default="planned")

    def __str__(self):
        return f"{self.type} - {self.farm.name}"


# =====================
# Agronomist Assignment
# =====================
class AgronomistAssignment(models.Model):
    agronomist = models.ForeignKey(AgronomistProfile, on_delete=models.CASCADE, related_name="assignments")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="assignments")
    role_on_farm = models.CharField(max_length=16, default="lead")
    assigned_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.agronomist} → {self.farm}"


# =====================
# Activity Model
# =====================
class Activity(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="activities")
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    agronomist = models.ForeignKey(AgronomistProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")

    type_code = models.CharField(max_length=32, default="other")
    date = models.DateField(default=timezone.now)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=8, default="UNIT")
    cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.type_code} @ {self.farm.name}"


# =====================
# Evaluation Model
# =====================
class Evaluation(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="evaluations")
    agronomist = models.ForeignKey(AgronomistProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="evaluations")
    season_code = models.CharField(max_length=32)
    date = models.DateField(default=timezone.now)

    yield_ton = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yield_ton_per_ha = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    recommendations = models.TextField(blank=True)

    def __str__(self):
        return f"Evaluation {self.season_code} - {self.farm.name}"