from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_page(request):
    # Redirect already-logged-in users
    if request.user.is_authenticated:
        return redirect('homepage')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)  # log the user in (session-based)
            return redirect('homepage')  # <-- this should redirect to your homepage
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")

def logout_page(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def homepage(request):
    return render(request, "homepage.html")