import jwt
import requests
import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.functions import ExtractWeek, ExtractYear
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View as _View
from onemsdk.schema.v1 import (
    Response,
    Menu, MenuItem, MenuItemType, MenuMeta, MenuItemFormItem,
    Form, FormItem, FormItemType, FormMeta, MenuFormItemMeta
)

from .models import Event
from .helpers import truncatechars


class View(_View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *a, **kw):
        return super(View, self).dispatch(*a, **kw)

    def get_user(self):
        # return User.objects.filter()[0]
        token = self.request.headers.get('Authorization')
        if token is None:
            raise PermissionDenied

        data = jwt.decode(token.replace('Bearer ', ''), key='87654321')
        user, created = User.objects.get_or_create(
                id=data['sub'], username=str(data['sub']),
                is_staff=data['is_admin']
        )
        headers = {
            'X-API-KEY': settings.APP_APIKEY_POC,
            'Content-Type': 'application/json'
        }
        std_url = settings.RESTD_API_URL_POC.format(
            endpoint='users/{}'
        ).format(user.id)
        response = requests.get(url=std_url, headers=headers)
        if response.status_code == 200 and created:
            response = response.json()
            user_names = ['first_name', 'last_name']
            for user_name in user_names:
                user_data = response.get(user_name)
                if user_data:
                    setattr(user, user_name, user_data)
        user.save()
        return user

    def to_response(self, content):
        response = Response(content=content)
        return HttpResponse(response.json(),
                            content_type='application/json')


class HomeView(View):
    http_method_names = ['get']

    def get(self, request):
        all_events = (Event.objects.annotate(
            year=ExtractYear('start_datetime')
        ).annotate(
            start_week=ExtractWeek('start_datetime')
        ))
        today = datetime.datetime.today()
        current_year = today.isocalendar()[0]
        current_week = today.isocalendar()[1]

        this_week_events = []
        future_events = []
        past_events = []
        for event in all_events:
            if event.year == current_year and event.start_week == current_week:
                this_week_events.append(event)
            elif (
                event.year == current_year and event.start_week > current_week
            ) or event.year > current_year:
                future_events.append(event)
            else:
                past_events.append(event)

        menu_items = [
            MenuItem(description='Search',
                     method='GET',
                     path=reverse('search_wizard'))
        ]
        if not this_week_events:
            menu_items.append(MenuItem(description='No events this week'))
        else:
            menu_items.append(
                MenuItem(description='This week events ({})'.format(
                             len(this_week_events)
                         ),
                         method='GET',
                         path=reverse('events', args=('current_week',)))
            )
        if not future_events:
            menu_items.append(MenuItem(description='No future events'))
        else:
            menu_items.append(
                MenuItem(description='Future evens ({})'.format(
                             len(future_events)
                         ),
                         method='GET',
                         path=reverse('events', args=('future_events',)))
            )
        if not past_events:
            menu_items.append(MenuItem(description='No past events'))
        else:
            menu_items.append(
                MenuItem(description='Past evens ({})'.format(
                             len(past_events)
                         ),
                         method='GET',
                         path=reverse('events', args=('past_events',)))
            )
        user = self.get_user()
        if user.is_staff:
            menu_items.insert(0, MenuItem(description='Add event',
                                          method='GET',
                                          path=reverse('add_event')))

        # check to see if we have notifications set in cache
        if cache.get('event_added'):
            menu_items.insert(0, MenuItem(
                description='Event added successfully')
            )
            cache.delete('event_added')
        if cache.get('event_edited'):
            menu_items.insert(0, MenuItem(
                description='Event edited successfully'
            ))
            cache.delete('event_edited')
        if cache.get('event_deleted'):
            menu_items.insert(0, MenuItem(
                description='Event deleted successfully'
            ))
            cache.delete('event_deleted')
        content = Menu(body=menu_items, header='menu')
        return self.to_response(content)


class SearchView(View):
    http_method_names = ['get', 'post']

    def get(self, request):
        form_items = [
            FormItem(type=FormItemType.string, name='keyword',
                     description='Send keywords to search',
                     header='search', footer='Reply keywords')
        ]
        content = Form(body=form_items, method='POST',
                       path=reverse('search_wizard'),
                       meta=FormMeta(skip_confirmation=True))
        return self.to_response(content)

    def post(self, request):
        keyword = request.POST['keyword']
        events = Event.objects.filter(Q(description__icontains=keyword))
        if not events:
            form_items = [
                FormItem(type=FormItemType.string, name='keyword',
                         description='No results found. Please try again '
                                     'with different keywords',
                         header='search', footer='Reply keywords')
            ]
            content = Form(body=form_items, method='POST',
                           path=reverse('search_wizard'),
                           meta=FormMeta(skip_confirmation=True))
        else:
            menu_items = []
            for event in events:
                menu_items.append(MenuItem(
                    description=truncatechars(event.description, 30),
                    method='GET', path=event.get_absolute_url()
                ))
            content = Menu(body=menu_items,
                           header='search: {}'.format(keyword))
        return self.to_response(content)


class EventsView(View):
    http_method_names = ['get']

    def get(self, request, category):
        all_events = (Event.objects.annotate(
            year=ExtractYear('start_datetime')
        ).annotate(
            start_week=ExtractWeek('start_datetime')
        ))
        today = datetime.datetime.today()
        current_year = today.isocalendar()[0]
        current_week = today.isocalendar()[1]

        events = []
        if category == 'current_week':
            for event in all_events:
                if event.year == current_year and event.start_week == current_week:
                    events.append(event)
        elif category == 'future_events':
            for event in all_events:
                if (
                    event.year == current_year and event.start_week > current_week
                ) or event.year > current_year:
                    events.append(event)
        else:
            for event in all_events:
                if (
                    event.year == current_year and event.start_week < current_week
                ) or event.year < current_year:
                    events.append(event)
        menu_items = []
        for event in events:
            menu_items.append(MenuItem(
                description=truncatechars(event.description, 30),
                method='GET', path=event.get_absolute_url()
            ))
        content = Menu(body=menu_items, header='menu')
        return self.to_response(content)


class EventView(View):
    http_method_names = ['get']

    def get(self, request, id):
        try:
            event = Event.objects.filter(id=id)[0]
        except IndexError:
            return self.to_response(Menu([
                MenuItem(description='Event unavailable'),
            ], header='unavailable', footer='Reply MENU'))

        menu_items = [
            MenuItem(description='Description: {}'.format(event.description)),
            MenuItem(description='Starting {date_time}'.format(
                date_time='{:%d-%m-%Y at %H:%M}'.format(event.start_datetime)
            )),
            MenuItem(description='Ending {date_time}'.format(
                date_time='{:%d-%m-%Y at %H:%M}'.format(event.end_datetime)
            ))
        ]
        header = 'details'
        footer = 'Reply BACK/MENU'
        user = self.get_user()
        if user.is_staff:
            menu_items.append(MenuItem(
                description='Edit/Delete',
                method='GET', path=reverse('edit_event', args=(event.id, 'edit'))
            ))
            header = 'admin menu'
            footer = None
        content = Menu(body=menu_items, header=header, footer=footer)
        return self.to_response(content)


class AddEventView(View):
    http_method_names = ['get', 'post']

    def get(self, request):
        form_items = [
            FormItem(type=FormItemType.string, name='description',
                     description='Send the description',
                     header='description', footer='Reply text'),
            FormItem(type=FormItemType.string, name='start_datetime',
                     description='\n'.join([
                         'Send the starting date and time',
                         'Example: 31-12-2020 12:00'
                     ]),
                     header='starting date time', footer='Reply with date and time'),
            FormItem(type=FormItemType.string, name='end_datetime',
                     description='\n'.join([
                         'Send the ending date and time',
                         'Example: 31-12-2020 14:00'
                     ]),
                     header='ending date time', footer='Reply with date and time'),
        ]

        content = Form(body=form_items, method='POST',
                       path=reverse('add_event'),
                       meta=FormMeta(skip_confirmation=True))
        return self.to_response(content)

    def post(self, request):
        try:
            event_create = Event.objects.create(
                description=request.POST['description'],
                start_datetime=datetime.datetime.strptime(
                    request.POST['start_datetime'], '%d-%m-%Y %H:%M'
                ),
                end_datetime=datetime.datetime.strptime(
                    request.POST['end_datetime'], '%d-%m-%Y %H:%M'
                )
            )
            event_create.save()
            cache.set('event_added', True)
        except Exception:
            form_items = [
                FormItem(type=FormItemType.string, name='add_event',
                         description='Event not added. Please check your input'
                                     ' format and try again.',
                         header='add event', footer='Reply BACK')
            ]
            content = Form(body=form_items, method='GET',
                           path=reverse('home'),
                           meta=FormMeta(skip_confirmation=True))
            return self.to_response(content)

        return HttpResponseRedirect(reverse('home'))


class EditEventView(View):
    http_method_names = ['get', 'post', 'delete']

    def get(self, request, **kwargs):
        try:
            event = Event.objects.filter(id=kwargs['id'])[0]
        except IndexError:
            return self.to_response(Menu([
                MenuItem(description='Event unavailable')
            ], header='Unavailable', footer='Reply MENU'))

        menu_items = [
            MenuItem(
                description='Edit description: {}'.format(
                    truncatechars(event.description, 30)
                ),
                method='POST',
                path=reverse('edit_event', args=(event.id, 'description'))
            ),
            MenuItem(
                description='Edit starting date time: {date_time}'.format(
                    date_time='{:%d-%m-%Y %H:%M}'.format(event.start_datetime)
                ),
                method='POST',
                path=reverse('edit_event', args=(event.id, 'start_datetime'))
            ),
            MenuItem(
                description='Edit ending date time: {date_time}'.format(
                    date_time='{:%d-%m-%Y %H:%M}'.format(event.end_datetime)
                ),
                method='POST',
                path=reverse('edit_event', args=(event.id, 'end_datetime'))),
            MenuItem(
                description='Delete',
                method='DELETE',
                path=reverse('edit_event', args=(event.id, 'delete')))
        ]
        content = Menu(body=menu_items, header='edit/delete')
        return self.to_response(content)

    def post(self, request, **kwargs):
        event = Event.objects.filter(id=kwargs['id'])[0]
        event_type = kwargs['type']
        event_content = getattr(event, event_type)
        # check if we are at the beginning of the wizard
        if not request.POST:
            form_items = [
                FormItem(type=FormItemType.string, name=event_type,
                         description='\n'.join([
                             'Current {event_type}: {event_content}'.format(
                                 event_type=event_type,
                                 event_content='{:%d-%m-%Y %H:%M}'.format(
                                     event_content
                                 ) if isinstance(event_content, datetime.datetime) else event_content
                             ),
                             'Send input to edit'
                         ]),
                         header='edit {event_type}'.format(
                             event_type=event_type
                         ),
                         footer='Reply with input/BACK')
            ]
            content = Form(body=form_items, method='POST',
                           path=reverse(
                               'edit_event', args=(kwargs['id'], event_type)
                           ),
                           meta=FormMeta(skip_confirmation=True))
            return self.to_response(content)
        else:
            try:
                if event_type in ['start_datetime', 'end_datetime']:
                    user_input = datetime.datetime.strptime(
                        request.POST[event_type], '%d-%m-%Y %H:%M'
                    )
                else:
                    user_input = request.POST[event_type]
                setattr(event, event_type, user_input)
                event.save()
                cache.set('event_edited', True)
            except Exception:
                form_items = [
                    FormItem(type=FormItemType.string, name='edit_event',
                             description='\n'.join([
                                 'Event not edited. Please check your input format and try again.',
                                 'Example for date and time format: 31-12-2020 12:00'

                             ]),
                             header='edit event', footer='Reply BACK')
                ]
                content = Form(body=form_items, method='GET',
                               path=reverse('home'),
                               meta=FormMeta(skip_confirmation=True))
                return self.to_response(content)
        return HttpResponseRedirect(reverse('home'))

    def delete(self, request, **kwargs):
        event = Event.objects.filter(id=kwargs['id'])[0]
        event.delete()
        cache.set('event_deleted', True)
        return HttpResponseRedirect(reverse('home'))
