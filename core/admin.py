from django.contrib import admin, messages
from django.core.mail import send_mail
from .models import User, Car, Booking


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_active", "is_approved")
    list_filter = ("role", "is_approved", "is_active")
    search_fields = ("username", "email", "company_name")
    ordering = ("role", "username")
    actions = ["approve_selected_owners"]

    fieldsets = (
        ("Account Info", {"fields": ("username", "email", "phone", "company_name")}),
        ("Permissions", {"fields": ("role", "is_active", "is_approved")}),
    )

    def approve_selected_owners(self, request, queryset):
        """Admin bulk action: Approve multiple owners."""
        owners = queryset.filter(role="owner", is_approved=False)
        if not owners.exists():
            self.message_user(request, "No pending owners found.", level=messages.WARNING)
            return

        count = 0
        for owner in owners:
            owner.is_approved = True
            owner.is_active = True
            owner.save()
            count += 1

            try:
                send_mail(
                    subject="✅ Account Approved",
                    message=(
                        f"Hello {owner.username},\n\n"
                        "Your owner account has been approved by the admin.\n"
                        "You can now log in and start adding your cars.\n\n"
                        "Best regards,\nRoyal Cars Team"
                    ),
                    from_email=None,
                    recipient_list=[owner.email],
                    fail_silently=True,
                )
            except Exception as e:
                self.message_user(
                    request, f"⚠️ Email not sent to {owner.email}: {e}", level=messages.WARNING
                )

        self.message_user(
            request,
            f"✅ {count} owner account(s) approved successfully.",
            level=messages.SUCCESS,
        )

    approve_selected_owners.short_description = "Approve selected owners"


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "year", "transmission", "price", "mileage")
    list_filter = ("year", "transmission")
    search_fields = ("name", "year", "owner__username")
    ordering = ("-year", "name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "car",
        "pickup_location",
        "drop_location",
        "pickup_date",
        "pickup_time",
        "status",
    )
    list_filter = ("status", "pickup_date")
    search_fields = ("user__username", "car__name")
    ordering = ("-pickup_date",)

    def save_model(self, request, obj, form, change):
        """Detect status changes and send appropriate email notifications."""
        if change:
            old_obj = Booking.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                subject, message = None, None

                if obj.status == "approved":
                    subject = "✅ Booking Approved"
                    message = (
                        f"Hello {obj.user.username},\n\n"
                        f"Your booking has been approved!\n\n"
                        f"Car: {obj.car.name}\n"
                        f"Pickup: {obj.pickup_location}\n"
                        f"Drop: {obj.drop_location}\n"
                        f"Date: {obj.pickup_date}\n"
                        f"Time: {obj.pickup_time}\n\n"
                        "Thank you for choosing Royal Cars!"
                    )

                elif obj.status == "rejected":
                    subject = "❌ Booking Rejected"
                    message = (
                        f"Hello {obj.user.username},\n\n"
                        f"Unfortunately, your booking has been rejected.\n\n"
                        f"Car: {obj.car.name}\n"
                        f"Pickup: {obj.pickup_location}\n"
                        f"Date: {obj.pickup_date} {obj.pickup_time}\n\n"
                        "You may contact us for further details."
                    )

                if subject and message:
                    try:
                        send_mail(
                            subject,
                            message,
                            from_email=None,
                            recipient_list=[obj.user.email],
                            fail_silently=True,
                        )
                        self.message_user(
                            request, f"📧 Email sent to {obj.user.email}", level=messages.SUCCESS
                        )
                    except Exception as e:
                        self.message_user(
                            request, f"⚠️ Failed to send email: {e}", level=messages.WARNING
                        )

        super().save_model(request, obj, form, change)