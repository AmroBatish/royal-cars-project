from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings

from .models import Booking, Car

User = get_user_model()


# ===========================
# PUBLIC PAGES
# ===========================
def index(request):
    owners = User.objects.filter(role="owner", is_approved=True)
    cars = Car.objects.all()
    return render(request, "index.html", {"owners": owners, "cars": cars})


def about(request):
    return render(request, "about.html")


def service(request):
    return render(request, "service.html")


def team(request):
    return render(request, "team.html")


def testimonial(request):
    return render(request, "testimonial.html")


def car(request):
    cars = Car.objects.all()
    return render(request, "car.html", {"cars": cars})


def detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    return render(request, "detail.html", {"car": car})

def payment(request):
    return render(request, 'payment.html')

# ===========================
# AUTHENTICATION
# ===========================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if not user:
            messages.error(request, "❌ Invalid username or password.")
            return redirect("login")

        if user.role == "owner" and not user.is_approved:
            messages.error(request, "⚠️ Your account is pending admin approval.")
            return redirect("login")

        login(request, user)
        return redirect("index")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "✅ Logged out successfully")
    return redirect("login")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone", "")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "❌ Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "❌ Username already exists.")
            return redirect("register")

        user = User.objects.create_user(username=username, email=email, password=password, phone=phone)
        login(request, user)
        messages.success(request, "🎉 Account created successfully.")
        return redirect("index")

    return render(request, "register.html")


def register_owner_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        company_name = request.POST.get("company_name", "")
        phone = request.POST.get("phone", "")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "❌ Passwords do not match.")
            return redirect("register_owner")

        if User.objects.filter(username=username).exists():
            messages.error(request, "❌ Username already exists.")
            return redirect("register_owner")

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            phone=phone,
            company_name=company_name,
            role="owner",
            is_approved=False,
        )

        messages.info(request, "✅ Account created. Wait for admin approval before login.")
        return redirect("login")

    return render(request, "register_owner.html")


# ===========================
# PROFILE & DASHBOARD
# ===========================
@login_required(login_url="login")
def profile_view(request):
    return render(request, "profile.html", {"user": request.user})


@login_required(login_url="login")
def owner_dashboard(request):
    if request.user.role != "owner":
        return redirect("index")

    cars = request.user.cars.all()
    bookings = Booking.objects.filter(car__owner=request.user)
    return render(request, "owner_dashboard.html", {"cars": cars, "bookings": bookings})


@login_required(login_url="login")
def add_car(request):
    if request.user.role != "owner":
        return redirect("index")

    if request.method == "POST":
        Car.objects.create(
            owner=request.user,
            name=request.POST.get("name"),
            year=request.POST.get("year"),
            transmission=request.POST.get("transmission"),
            mileage=request.POST.get("mileage"),
            price=request.POST.get("price"),
            description=request.POST.get("description", ""),
            image=request.FILES.get("image"),
        )
        messages.success(request, "🚗 Car added successfully.")
        return redirect("owner_dashboard")

    return redirect("owner_dashboard")


# ===========================
# BOOKINGS
# ===========================
@login_required(login_url="login")
def booking_view(request):
    if request.method == "POST":
        car = get_object_or_404(Car, pk=request.POST.get("car"))
        required_fields = [request.POST.get(f) for f in ["pickup_location", "drop_location", "pickup_date", "pickup_time"]]

        if not all(required_fields):
            return JsonResponse({"status": "error", "message": "Please fill all required fields."}, status=400)

        Booking.objects.create(
            user=request.user,
            car=car,
            pickup_location=request.POST.get("pickup_location"),
            drop_location=request.POST.get("drop_location"),
            pickup_date=request.POST.get("pickup_date"),
            pickup_time=request.POST.get("pickup_time"),
            special_request=request.POST.get("special_request", ""),
        )

        messages.success(request, "✅ Booking created successfully.")

        return JsonResponse({"status": "success", "message": "Booking successful! Please wait for confirmation."})

    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)


@login_required(login_url="login")
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user)
    booking.status = "approved"
    booking.save()

    send_mail(
        "✅ Booking Approved",
        f"Hello {booking.user.username}, your booking for {booking.car.name} has been approved.",
        "noreply@royalcars.com",
        [booking.user.email],
        fail_silently=True,
    )

    messages.success(request, "✅ Booking approved and email sent.")
    return redirect("owner_dashboard")


@login_required(login_url="login")
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, car__owner=request.user)
    booking.status = "rejected"
    booking.save()

    send_mail(
        "❌ Booking Rejected",
        f"Hello {booking.user.username}, your booking for {booking.car.name} has been rejected.",
        "noreply@royalcars.com",
        [booking.user.email],
        fail_silently=True,
    )

    messages.warning(request, "❌ Booking rejected.")
    return redirect("owner_dashboard")


# ===========================
# SEARCH & COMPANIES
# ===========================
def search_cars(request):
    query = request.GET.get("q", "")
    cars = Car.objects.filter(
        Q(name__icontains=query) |
        Q(transmission__icontains=query) |
        Q(year__icontains=query)
    )
    results = [{
        "id": car.id,
        "name": car.name,
        "year": car.year,
        "transmission": car.transmission,
        "mileage": car.mileage,
        "price": str(car.price),
        "image": car.image.url if car.image else "",
    } for car in cars]

    return JsonResponse({"results": results})


def companies_list(request):
    owners = User.objects.filter(role="owner", is_approved=True)
    return render(request, "companies.html", {"owners": owners})


def owner_cars(request, owner_id):
    owner = get_object_or_404(User, id=owner_id, role="owner")
    cars = Car.objects.filter(owner=owner)
    return render(request, "owner_cars.html", {"owner": owner, "cars": cars})


def owner_profile(request, owner_id):
    owner = get_object_or_404(User, id=owner_id, role="owner")
    cars = Car.objects.filter(owner=owner)
    return render(request, "owner_cars.html", {"owner": owner, "cars": cars})


# ===========================
# CONTACT FORM
# ===========================
def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not all([name, email, subject, message]):
            messages.error(request, "❌ Please fill in all fields.")
            return redirect("contact")

        to_email = getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)
        full_subject = f"[Royal Cars Contact] {subject}"
        full_message = f"From: {name} <{email}>\n\nMessage:\n{message}"

        try:
            send_mail(full_subject, full_message, settings.DEFAULT_FROM_EMAIL, [to_email])
            messages.success(request, "✅ Your message has been sent successfully.")
        except Exception as e:
            messages.error(request, f"❌ Failed to send message: {e}")

        return redirect("contact")

    return render(request, "contact.html", {"CONTACT_EMAIL": getattr(settings, "CONTACT_EMAIL", None)})