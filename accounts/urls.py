from django.urls import path
from .views import login_page, logout_page, select_farm, switch_farm

urlpatterns = [
    path('login/', login_page, name='login'),
    path('logout/', logout_page, name='logout'),
    path('select-farm/', select_farm, name='select_farm'),
    path('switch-farm/', switch_farm, name='switch_farm'),
]
