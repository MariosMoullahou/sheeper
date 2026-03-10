from django.shortcuts import render, get_object_or_404, redirect
from .models import Sheep,BirthEvent,Milk,CalendarEvent
from sheepfold.forms import SheepForm,SheepingForm,MilkForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required
from .forms import SheepingForm
from .serializers import MilkSerializer,SheepData,BirthEventSerializer,CalendarEventSerializer

@login_required(login_url='login')
def homepage(request):
    sheep = Sheep.objects.all()
    return render(request, "homepage.html", {"sheep": sheep})

@login_required(login_url='login')
def sheep_detail(request, pk):
    sheep = get_object_or_404(Sheep, pk=pk)
    return render(request, "sheep_detail.html", {"sheep": sheep})

@login_required(login_url='login')
def sheep_create(request):
    form = SheepForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("homepage")
    return render(request, "sheep_form.html", {"form": form})

@login_required(login_url='login')
def milking(request):
    milk = Milk.objects.all()  # fetch existing records
    sheep = Sheep.objects.all()
    return render(request, "milking.html", {"sheep": sheep, "milk": milk})

@login_required(login_url='login')
@api_view(['GET', 'POST'])
def milking_api(request):
    if request.method == 'GET':
        milk = Milk.objects.all()
        serializer = MilkSerializer(milk, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        print(request.data)
        serializer = MilkSerializer(data=request.data)  # <- use request.data
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@login_required(login_url='login')
@api_view(['GET', 'POST'])
def birthevent_api(request):
    if request.method == 'GET':
        milk = BirthEvent.objects.all()
        serializer = BirthEventSerializer(milk, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        print(request.data)
        serializer = BirthEventSerializer(data=request.data)  # <- use request.data
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@login_required(login_url='login')
@api_view(['GET','POST'])
def sheep_data_api(request):
    if request.method == 'GET':
        sheep = Sheep.objects.all()
        serializer = SheepData(sheep, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        print(request.data)
        serializer = SheepData(data= request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

@login_required(login_url='login')
def lamping(request):
    if request.method == 'POST':
        form = SheepingForm(request.POST)
        print(form)
        if form.is_valid():
            birth_event = form.save(commit=False)
            birth_event.save()

            new_lamb_names = request.POST.get('new_lambs', '').split(',')

            for name in new_lamb_names:
                name = name.strip()
                if name:
                    lamb = Sheep.objects.create(
                        name=name,
                    )
                    birth_event.lambs.add(lamb)

            form.save_m2m()

            return redirect('homepage')
    else:
        form = SheepingForm()

    return render(request, 'lamping.html', {'form': form})

@login_required(login_url='login')
def calendar_view(request):
    return render(request, "calendar.html")

@login_required(login_url='login')
@api_view(['GET','POST'])
def calendar_data_api(request):
    if request.method == 'GET':
        calendarEvent = CalendarEvent.objects.all()
        serializer = CalendarEventSerializer(calendarEvent, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        print(request.data)
        serializer = CalendarEventSerializer(data= request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

