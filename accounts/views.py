from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .helpers import get_active_farm, set_active_farm, get_user_farms


def login_page(request):
    if request.user.is_authenticated:
        return redirect('select_farm')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('select_farm')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")


def logout_page(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def select_farm(request):
    """Let the user pick which farm to work in, or auto-select if only one."""
    farms = get_user_farms(request.user)

    if not farms.exists():
        messages.error(request, "You are not a member of any farm.")
        return render(request, "select_farm.html", {"farms": farms})

    # Auto-select if only one farm
    if farms.count() == 1:
        set_active_farm(request, farms.first())
        return redirect('homepage')

    if request.method == "POST":
        farm_id = request.POST.get("farm_id")
        farm = get_object_or_404(farms, pk=farm_id)
        set_active_farm(request, farm)
        return redirect('homepage')

    return render(request, "select_farm.html", {"farms": farms})


@login_required(login_url='login')
def switch_farm(request):
    """Clear active farm and go back to selection."""
    request.session.pop('active_farm_id', None)
    return redirect('select_farm')
