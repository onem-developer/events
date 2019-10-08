from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path(
        'search_wizard/', views.SearchView.as_view(),
        name='search_wizard'
    ),
    path(
        'events/<str:category>/', views.EventsView.as_view(),
        name='events'
    ),
    path(
        'event/<int:id>/', views.EventView.as_view(),
        name='event'
    ),
    path(
        'add_event', views.AddEventView.as_view(),
        name='add_event'
    ),
    path(
        'edit_event/<int:id>/<str:type>', views.EditEventView.as_view(),
        name='edit_event'
    ),
]
