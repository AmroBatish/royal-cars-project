from django.shortcuts import render, redirect, get_object_or_404 , HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, date 
from django.utils import timezone
import stripe
from .models import Booking, Car , Review, User
from django.views.decorators.http import require_POST
from django.urls import reverse

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
    reviews = Review.objects.filter(car=car).select_related("user")
    return render(request, "detail.html", {"car": car,
        "reviews": reviews,})

# def payment_success(request):
#     messages.success(request, "✅ Payment completed successfully!")
#     return redirect("profile")

def payment_cancel(request):
    messages.warning(request, "⚠️ Payment canceled.")
    return redirect("profile")
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
    return render(request, "owner_dashboard.html", {"cars": cars, "bookings": bookings , "request": request,} )

@login_required(login_url="login")
def add_car(request):
    if request.user.role != "owner":
        return JsonResponse({"success": False, "error": "Unauthorized"})

    if request.method == "POST":
        try:
            # 🔹 التحقق من وجود سيارة بنفس الاسم والسنة لنفس المالك (منع التكرار)
            name = request.POST.get("name")
            year = request.POST.get("year")
            if Car.objects.filter(owner=request.user, name=name, year=year).exists():
                return JsonResponse({
                    "success": False,
                    "error": "You already added a car with this name and year."
                })

            # 🔹 إنشاء السيارة
            car = Car.objects.create(
                owner=request.user,
                name=name,
                year=year,
                transmission=request.POST.get("transmission"),
                mileage=request.POST.get("mileage"),
                price=request.POST.get("price"),
                description=request.POST.get("description", ""),
                image=request.FILES.get("image"),
            )

            # 🔹 رسالة نجاح + إرجاع JSON للـ AJAX
            return JsonResponse({
                "success": True,
                "id": car.id,
                "name": car.name,
                "year": car.year,
                "transmission": car.transmission,
                "mileage": car.mileage,
                "price": float(car.price),
                "image_url": car.image.url if car.image else None
            })

        except Exception as e:
            # 🔹 حذف السيارة لو حصل خطأ بعد الإنشاء
            if 'car' in locals():
                car.delete()
            return JsonResponse({
                "success": False,
                "error": f"Error while adding car: {str(e)}"
            })

    return JsonResponse({"success": False, "error": "Invalid request method"})

@login_required(login_url="login")
def edit_car(request):
    if request.method == 'POST':
        car_id = request.POST.get('car_id')
        car = get_object_or_404(Car, id=car_id, owner=request.user)

        car.name = request.POST.get('name')
        car.year = request.POST.get('year')
        car.transmission = request.POST.get('transmission')
        car.mileage = request.POST.get('mileage')
        car.price = request.POST.get('price')
        car.description = request.POST.get('description')

        if 'image' in request.FILES:
            car.image = request.FILES['image']

        car.save()
        return JsonResponse({
            'success': True,
            'id': car.id,
            'name': car.name,
            'year': car.year,
            'transmission': car.transmission,
            'mileage': car.mileage,
            'price': str(car.price),
            'description': car.description,
            'image_url': car.image.url if car.image else ''
        })
    return JsonResponse({'success': False})

@login_required(login_url="login")
def delete_car(request, car_id):
    if request.method == 'POST':
        car = get_object_or_404(Car, id=car_id, owner=request.user)
        car.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

# ===========================
# BOOKINGS
# ===========================
@login_required(login_url="login")
def booking_view(request):
    if getattr(request.user, "role", None) == "owner":
        return JsonResponse({"status": "error", "message": "Owners cannot create bookings."}, status=403)
    
    if request.method == "POST":
        car = get_object_or_404(Car, pk=request.POST.get("car"))
        
        # ✅ NEW: أضفنا return_date و return_time ضمن الحقول المطلوبة
        required_fields = [
            request.POST.get(f) 
            for f in ["pickup_location", "drop_location", "pickup_date", "pickup_time", "return_date", "return_time"]
        ]

        if not all(required_fields):
            return JsonResponse({"status": "error", "message": "Please fill all required fields."}, status=400)

        pickup_date_str = request.POST.get("pickup_date")
        return_date_str = request.POST.get("return_date")

        pickup_date = datetime.strptime(pickup_date_str, "%Y-%m-%d").date()
        return_date = datetime.strptime(return_date_str, "%Y-%m-%d").date()
        today = date.today()
        if pickup_date < today:
            return JsonResponse({
                "status": "error",
                "message": "Pickup date cannot be in the past."
            }, status=400)
        # ✅ NEW: تحقق من ترتيب التواريخ (أن تاريخ الإرجاع بعد الاستلام)
        if return_date < pickup_date:
            return JsonResponse({"status": "error", "message": "Return date must be after pickup date."}, status=400)

        # ✅ NEW: تحقق من وجود تعارض في الحجوزات
        from django.db import transaction
        with transaction.atomic():
            overlapping = Booking.objects.filter(
                car=car,
                status__in=["pending", "approved", "paid"],
                pickup_date__lt=return_date,
                return_date__gt=pickup_date,
            ).exists()

            if overlapping:
                return JsonResponse({
                    "status": "error",
                    "message": "🚫 This car is already booked during the selected dates."
                }, status=400)

            # إنشاء الحجز
            Booking.objects.create(
                user=request.user,
                car=car,
                pickup_location=request.POST.get("pickup_location"),
                drop_location=request.POST.get("drop_location"),
                pickup_date=request.POST.get("pickup_date"),
                pickup_time=request.POST.get("pickup_time"),
                # ✅ NEW: أضفنا حقول الإرجاع الجديدة
                return_date=request.POST.get("return_date"),
                return_time=request.POST.get("return_time"),
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

@login_required(login_url="login")
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related("car")
    today = timezone.now().date()

    for b in bookings:
        b.has_comment = hasattr(b, "review")

    return render(request, "my_bookings.html", {
        "bookings": bookings,
        "today": today,
    })

@login_required(login_url="login")
def pay_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != "approved":
        messages.warning(request, "⚠️ You can only pay after the owner approves your booking.")
        return redirect("my_bookings")
    # مبلغ الدفع (سعر اليوم الواحد) بالسنت
    amount_cents = int(float(booking.car.price) * 100)

    # جلسة Stripe Checkout
    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"{booking.car.name} ",
                                "description": f"🚗 Pickup: {booking.pickup_location} → 🏁 Drop: {booking.drop_location}",
                                "images": [f"{settings.DOMAIN}{booking.car.image.url}"],
                            },
                            "unit_amount": amount_cents,  # بالدولار
                            
                        },
                        "quantity": 1,
                    }
                ],
        metadata={"booking_id": str(booking.id), "user_id": str(request.user.id)},
        success_url=f"{settings.DOMAIN}/payment/success/?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.DOMAIN}/payment/cancel/?booking={booking.id}",
    )

    return HttpResponseRedirect(session.url)


@login_required(login_url="login")
def payment_success(request):
    session_id = request.GET.get("session_id")

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        booking_id = session.metadata.get("booking_id")
    except Exception as e:
        booking_id = None
        print("⚠️ Stripe session not found:", e)

    if booking_id:
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)

            # ✅ تحديث حالة الحجز تلقائيًا إلى paid
            booking.status = "paid"
            booking.save()

            # ✉️ إرسال رسالة تأكيد بسيطة (اختياري)
            send_mail(
                "✅ Payment Successful - Royal Cars",
                f"Hello {request.user.username},\n\nYour payment for {booking.car.name} was successful! Your booking is now marked as paid.",
                "noreply@royalcars.com",
                [request.user.email],
                fail_silently=True,
            )

            messages.success(request, "✅ Payment successful! Your booking is now marked as paid.")
        except Booking.DoesNotExist:
            messages.error(request, "⚠️ Booking not found.")
    else:
        messages.error(request, "⚠️ Invalid payment confirmation.")

    return redirect(f"{reverse('my_bookings')}?show_contract=true&booking={booking_id}")

@login_required(login_url="login")
def payment_cancel(request):
    messages.info(request, "⏪ Payment canceled.")
    return redirect("profile")


stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)


@login_required(login_url="login")
@csrf_exempt
def create_checkout_session(request):
    if request.method == "POST":
        try:
            car = get_object_or_404(Car, pk=request.POST.get("car"))

            # إنشاء حجز مؤقت
            booking = Booking.objects.create(
                user=request.user,
                car=car,
                pickup_location=request.POST.get("pickup_location"),
                drop_location=request.POST.get("drop_location"),
                pickup_date=request.POST.get("pickup_date"),
                pickup_time=request.POST.get("pickup_time"),
                special_request=request.POST.get("special_request", ""),
            )

            # إنشاء جلسة الدفع
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"{booking.car.name} (1 day)",
                                "description": f"🚗 Pickup: {booking.pickup_location}→ 🏁 Drop: {booking.drop_location}",
                                "images": [f"{settings.DOMAIN}{booking.car.image.url}"],
                            },
                            "unit_amount": int(float(car.price) * 100),  # بالدولار
                            
                        },
                        "quantity": 1,
                    }
                ],
                 metadata={  # ✅ نحفظ البيانات هنا
                    "booking_id": str(booking.id),
                    "user_id": str(request.user.id)
                },
                success_url=f"{settings.DOMAIN}/payment/success/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.DOMAIN}/payment/cancel/?booking={booking.id}",
            )

            return JsonResponse({"url": checkout_session.url})
        except Exception as e:
            return JsonResponse({"error": str(e)})

    return JsonResponse({"error": "Invalid request"})



@login_required(login_url="login")
def add_comment(request, booking_id):
    from django.utils import timezone
    from .models import Review

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == "POST":
        rating = int(request.POST.get("rating", 5))
        comment = request.POST.get("comment", "").strip()

        if not comment:
            messages.error(request, "⚠️ Please write a comment before submitting.")
            return redirect("my_bookings")

        # تحقق من صلاحية إضافة تعليق
        if booking.status == "paid" and booking.return_date < timezone.now().date() and not hasattr(booking, "review"):
            Review.objects.create(
                booking=booking,
                car=booking.car,
                user=request.user,
                rating=rating,
                comment=comment,
            )
            messages.success(request, "✅ Your comment has been added successfully!")
        else:
            messages.error(request, "⚠️ You cannot comment on this booking.")
    return redirect("my_bookings")


@login_required
@require_POST
def approve_contract(request):
    booking_id = request.POST.get("booking_id")
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    # تاريخ اليوم
    today = timezone.now().strftime("%B %d, %Y")

    company_name = (
            booking.car.owner.company_name
            if booking.car and booking.car.owner and booking.car.owner.company_name
            else "Royal Cars Company"
        )
        # ✉️ نص العقد الكامل داخل البريد
    contract_text = f"""
==============================
   ROYAL CARS RENTAL AGREEMENT
==============================

Date: {today}
Company: {company_name}
Customer: {request.user.get_full_name() or request.user.username}
Car: {booking.car.name}
Pickup: {booking.pickup_location}
Drop: {booking.drop_location}
Rental Period: {booking.pickup_date} → {booking.return_date}
Price: ${booking.car.price}

------------------------------------------------------------
TERMS & CONDITIONS
------------------------------------------------------------
1. The renter agrees to operate the vehicle safely and in accordance with all traffic laws.
2. The renter is responsible for any damages, fines, or traffic violations during the rental period.
3. No smoking, racing, or illegal activity is permitted in the vehicle.
4. The vehicle must be returned in the same condition as received.
5. Fuel costs, tolls, and additional fees are the renter’s responsibility.
6. Payment has been received in full via Stripe.
7. Violation of these terms may result in early termination of the agreement.

------------------------------------------------------------
ACCEPTANCE
------------------------------------------------------------
By accepting this agreement electronically through Royal Cars,
the renter acknowledges full understanding and agreement to all terms above.

Digital Signature: {request.user.get_full_name() or request.user.username}
Date Signed: {today}

------------------------------------------------------------
Thank you for choosing {company_name}.
We look forward to serving you again!

{company_name} Team
www.royalcars.com
------------------------------------------------------------
"""

    # إرسال البريد
    send_mail(
        subject=f"✅ Rental Agreement Confirmation - {company_name}",
        message=contract_text,
        from_email="noreply@royalcars.com",
        recipient_list=[request.user.email],
        fail_silently=True,
    )

    return redirect("my_bookings")
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