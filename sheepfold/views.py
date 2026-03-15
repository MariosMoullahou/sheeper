from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Sheep, BirthEvent, Milk, CalendarEvent
from .forms import SheepForm, SheepingForm
from .serializers import MilkSerializer, SheepData, BirthEventSerializer, CalendarEventSerializer
from accounts.helpers import (
    get_active_farm, role_required, api_role_required,
)
from accounts.models import ROLE_FARMER, ROLE_ANALYST, ROLE_MANAGER


def _require_farm(request):
    """Return the active farm or None."""
    return get_active_farm(request)


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------

@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def homepage(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')

    sheep = Sheep.objects.filter(farm=farm)
    today = timezone.localdate()

    # Recent activity: last 10 items across sheep, milk, birth events
    recent_sheep = (
        Sheep.objects.filter(farm=farm)
        .order_by('-id')[:10]
        .values_list('earing', 'id')
    )
    recent_milk = (
        Milk.objects.filter(sheep__farm=farm)
        .select_related('sheep')
        .order_by('-id')[:10]
    )
    recent_births = (
        BirthEvent.objects.filter(mother__farm=farm)
        .select_related('mother')
        .order_by('-id')[:10]
    )

    activity = []
    for earing, sid in recent_sheep:
        activity.append({
            'icon': 'bi-plus-circle-fill',
            'color': 'var(--green-500)',
            'text': f'Sheep #{earing} added',
            'type': 'sheep',
        })
    for m in recent_milk:
        activity.append({
            'icon': 'bi-droplet-fill',
            'color': '#3b82f6',
            'text': f'Milk recorded for #{m.sheep.earing} — {m.milk}L on {m.date}',
            'type': 'milk',
        })
    for b in recent_births:
        lamb_count = b.lambs.count()
        activity.append({
            'icon': 'bi-lightning-fill',
            'color': '#f59e0b',
            'text': f'Birth event: #{b.mother.earing} — {lamb_count} lamb(s) on {b.date}',
            'type': 'birth',
        })
    activity = activity[:10]

    # Upcoming calendar events (next 5)
    upcoming_events = (
        CalendarEvent.objects.filter(farm=farm, start__gte=today)
        .order_by('start')[:5]
    )

    return render(request, "homepage.html", {
        "sheep": sheep,
        "farm": farm,
        "activity": activity,
        "upcoming_events": upcoming_events,
    })


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_detail(request, pk):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    sheep = get_object_or_404(Sheep, pk=pk, farm=farm)
    return render(request, "sheep_detail.html", {"sheep": sheep})


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_create(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    form = SheepForm(request.POST or None)
    if form.is_valid():
        sheep = form.save(commit=False)
        sheep.farm = farm
        sheep.save()
        return redirect("homepage")
    return render(request, "sheep_form.html", {"form": form})


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def milking(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    milk = Milk.objects.filter(sheep__farm=farm)
    sheep = Sheep.objects.filter(farm=farm)
    return render(request, "milking.html", {"sheep": sheep, "milk": milk})


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def lamping(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')

    if request.method == 'POST':
        form = SheepingForm(request.POST, farm=farm)
        if form.is_valid():
            birth_event = form.save(commit=False)
            birth_event.save()

            new_lamb_earings = request.POST.get('new_lambs', '').split(',')
            for earing in new_lamb_earings:
                earing = earing.strip()
                if earing:
                    lamb = Sheep.objects.create(earing=earing, farm=farm)
                    birth_event.lambs.add(lamb)

            form.save_m2m()
            return redirect('homepage')
    else:
        form = SheepingForm(farm=farm)

    return render(request, 'lamping.html', {'form': form})


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def calendar_view(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    return render(request, "calendar.html")


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------

@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def milking_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        milk = Milk.objects.filter(sheep__farm=farm)
        serializer = MilkSerializer(milk, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = MilkSerializer(data=request.data)
        if serializer.is_valid():
            sheep = serializer.validated_data['sheep']
            if sheep.farm_id != farm.pk:
                return Response(
                    {"sheep": "This sheep does not belong to your farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def milk_delete_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    milk = get_object_or_404(Milk, pk=pk, sheep__farm=farm)
    milk.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@login_required(login_url='login')
@api_view(['DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_delete_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    sheep = get_object_or_404(Sheep, pk=pk, farm=farm)
    sheep.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def birthevent_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        events = BirthEvent.objects.filter(mother__farm=farm)
        serializer = BirthEventSerializer(events, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BirthEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_data_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        sheep = Sheep.objects.filter(farm=farm)
        serializer = SheepData(sheep, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = SheepData(data=request.data)
        if serializer.is_valid():
            serializer.save(farm=farm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def calendar_data_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        events = CalendarEvent.objects.filter(farm=farm)
        serializer = CalendarEventSerializer(events, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = CalendarEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(farm=farm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
