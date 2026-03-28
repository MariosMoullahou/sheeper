from datetime import timedelta

from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import icalendar

from .models import Sheep, BirthEvent, Milk, HealthRecord, CalendarEvent
from .forms import SheepForm, SheepingForm
from .serializers import MilkSerializer, SheepData, BirthEventSerializer, HealthRecordSerializer, CalendarEventSerializer
from accounts.helpers import (
    get_active_farm, get_user_role, role_required, api_role_required,
)
from accounts.models import Farm, ROLE_FARMER, ROLE_ANALYST, ROLE_MANAGER


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
def health_view(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    sheep = Sheep.objects.filter(farm=farm)
    return render(request, "health.html", {"sheep": sheep})


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def bulk_milking(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    return render(request, "bulk_milking.html")


@login_required(login_url='login')
@role_required(ROLE_FARMER, ROLE_MANAGER)
def calendar_view(request):
    farm = _require_farm(request)
    if farm is None:
        return redirect('select_farm')
    return render(request, "calendar.html", {"calendar_token": farm.calendar_token})


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
@api_view(['PUT', 'DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def milk_detail_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    milk = get_object_or_404(Milk, pk=pk, sheep__farm=farm)

    if request.method == 'DELETE':
        milk.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = MilkSerializer(milk, data=request.data, partial=True)
    if serializer.is_valid():
        sheep = serializer.validated_data.get('sheep', milk.sheep)
        if sheep.farm_id != farm.pk:
            return Response(
                {"sheep": "This sheep does not belong to your farm."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['PUT', 'DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_detail_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    sheep = get_object_or_404(Sheep, pk=pk, farm=farm)

    if request.method == 'DELETE':
        sheep.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = SheepData(sheep, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def birthevent_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        events = (
            BirthEvent.objects.filter(mother__farm=farm)
            .select_related('mother')
            .prefetch_related('lambs')
            .order_by('-date')
        )
        serializer = BirthEventSerializer(events, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = BirthEventSerializer(data=request.data)
        if serializer.is_valid():
            mother = serializer.validated_data['mother']
            if mother.farm_id != farm.pk:
                return Response(
                    {"mother": "This sheep does not belong to your farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['PUT', 'DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def birthevent_detail_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    event = get_object_or_404(BirthEvent, pk=pk, mother__farm=farm)

    if request.method == 'DELETE':
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Only allow editing date and notes (mother/lambs are complex)
    data = {}
    if 'date' in request.data:
        data['date'] = request.data['date']
    if 'notes' in request.data:
        data['notes'] = request.data['notes']

    for key, value in data.items():
        setattr(event, key, value)
    event.save()

    serializer = BirthEventSerializer(event)
    return Response(serializer.data)


@login_required(login_url='login')
@api_view(['GET', 'POST'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def health_api(request):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        records = HealthRecord.objects.filter(farm=farm).select_related('sheep').order_by('-date')
        serializer = HealthRecordSerializer(records, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = HealthRecordSerializer(data=request.data)
        if serializer.is_valid():
            sheep = serializer.validated_data.get('sheep')
            if sheep and sheep.farm_id != farm.pk:
                return Response(
                    {"sheep": "This sheep does not belong to your farm."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.save(farm=farm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['PUT', 'DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def health_detail_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    record = get_object_or_404(HealthRecord, pk=pk, farm=farm)

    if request.method == 'DELETE':
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = HealthRecordSerializer(record, data=request.data, partial=True)
    if serializer.is_valid():
        sheep = serializer.validated_data.get('sheep', record.sheep)
        if sheep and sheep.farm_id != farm.pk:
            return Response(
                {"sheep": "This sheep does not belong to your farm."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['GET'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def sheep_profile_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    sheep = get_object_or_404(Sheep, pk=pk, farm=farm)

    # Basic info
    info = {
        "id": sheep.id,
        "earing": sheep.earing,
        "gender": sheep.get_gender_display(),
        "gender_code": sheep.gender,
        "birthdate": sheep.birthdate,
        "is_active": sheep.is_active,
        "mother": sheep.mother.earing if sheep.mother else None,
        "mother_id": sheep.mother_id,
    }

    # Children
    children = list(
        sheep.children.values('id', 'earing', 'gender', 'birthdate')
    )

    # Health records (individual + batch)
    health = list(
        HealthRecord.objects.filter(
            farm=farm
        ).filter(
            models.Q(sheep=sheep) | models.Q(is_batch=True)
        ).order_by('-date').values(
            'id', 'date', 'record_type', 'title', 'notes', 'next_due', 'is_batch'
        )[:50]
    )

    # Milk records
    milk = list(
        Milk.objects.filter(sheep=sheep).order_by('-date').values(
            'id', 'date', 'milk', 'is_active'
        )[:50]
    )

    # Birth events (as mother)
    births_as_mother = []
    for be in BirthEvent.objects.filter(mother=sheep).prefetch_related('lambs').order_by('-date')[:20]:
        births_as_mother.append({
            'id': be.id,
            'date': be.date,
            'notes': be.notes,
            'lambs': list(be.lambs.values('id', 'earing', 'gender')),
        })

    # Birth event where this sheep was born (as a lamb)
    born_in = None
    birth_event = sheep.birth_event.select_related('mother').first()
    if birth_event:
        born_in = {
            'id': birth_event.id,
            'date': birth_event.date,
            'mother': birth_event.mother.earing,
        }

    return Response({
        "info": info,
        "children": children,
        "health": health,
        "milk": milk,
        "births_as_mother": births_as_mother,
        "born_in": born_in,
    })


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
        all_farms = request.query_params.get('all_farms') == 'true'
        role = get_user_role(request.user)
        if all_farms and (role == ROLE_MANAGER or request.user.is_superuser):
            events = CalendarEvent.objects.select_related('farm').all()
        else:
            events = CalendarEvent.objects.select_related('farm').filter(farm=farm)
        serializer = CalendarEventSerializer(events, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = CalendarEventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(farm=farm)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url='login')
@api_view(['PUT', 'DELETE'])
@api_role_required(ROLE_FARMER, ROLE_MANAGER)
def calendar_detail_api(request, pk):
    farm = get_active_farm(request)
    if farm is None:
        return Response({"detail": "No active farm."}, status=status.HTTP_403_FORBIDDEN)

    event = get_object_or_404(CalendarEvent, pk=pk, farm=farm)

    if request.method == 'DELETE':
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = CalendarEventSerializer(event, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# iCal feed (no login — authenticated by secret token)
# ---------------------------------------------------------------------------

def calendar_feed(request, token):
    farm = get_object_or_404(Farm, calendar_token=token)

    cal = icalendar.Calendar()
    cal.add('prodid', '-//Sheeper//Farm Calendar//EN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', f'Sheeper - {farm.name}')

    for event in CalendarEvent.objects.filter(farm=farm):
        vevent = icalendar.Event()
        vevent.add('uid', f'sheeper-event-{event.pk}@sheeper')
        vevent.add('summary', event.title)
        vevent.add('dtstart', event.start)
        if event.end:
            vevent.add('dtend', event.end)
        else:
            vevent.add('dtend', event.start + timedelta(days=1))
        cal.add_component(vevent)

    response = HttpResponse(cal.to_ical(), content_type='text/calendar; charset=utf-8')
    return response
