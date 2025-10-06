from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('about/', views.about, name="about"),
    path('service/', views.service, name="service"),
    path('team/', views.team, name="team"),
    path('testimonial/', views.testimonial, name="testimonial"),
    path('contact/', views.contact, name="contact"),
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),
    path('register/', views.register_view, name="register"),
    path('register/owner/', views.register_owner_view, name="register_owner"),
    path('profile/', views.profile_view, name="profile"),
    path('car/', views.car, name="car"),
    path('detail/<int:pk>/', views.detail, name="detail"),
    path('search/', views.search_cars, name="search_cars"),
    path('booking/', views.booking_view, name="booking"),
    path('booking/<int:booking_id>/approve/', views.approve_booking, name="approve_booking"),
    path('booking/<int:booking_id>/reject/', views.reject_booking, name="reject_booking"),
    path('owner/dashboard/', views.owner_dashboard, name="owner_dashboard"),
    path('owner/add-car/', views.add_car, name="add_car"),
    path('owner/<int:owner_id>/cars/', views.owner_cars, name="owner_cars"),
    path('owner/<int:owner_id>/', views.owner_profile, name="owner_profile"),
    path('companies/', views.companies_list, name="companies_list"),
    path('payment/', views.payment, name='payment'),
]