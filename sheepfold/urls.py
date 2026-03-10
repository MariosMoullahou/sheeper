from django.urls import path
from . import views

urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("new/", views.sheep_create, name="sheep_create"),
    path("<int:pk>/", views.sheep_detail, name="sheep_detail"),
    path("lamping/",views.lamping, name="lamping"),
    path("milking/",views.milking, name="milking"),
    path('api/milk/', views.milking_api, name='milking-api'),
    path('api/sheep/',views.sheep_data_api, name='sheep-data-api'),
    path('api/birthevent/',views.birthevent_api, name='birthevent-data-api'),
    path("calendar/",views.calendar_view, name="calendar"),
    path('api/calendar/', views.calendar_data_api, name='calendar-api'),]
