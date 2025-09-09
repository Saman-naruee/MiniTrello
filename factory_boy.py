"""
Usage in django shell:
>>> from factory_boy import BoardFactory
>>> board = BoardFactory.create()
>>> board
<Board: Board object (1)>
"""
import factory
from factory.django import DjangoModelFactory
from django.conf import settings
from apps.boards.models import Board, List, Card, Membership


class BoardFactory(DjangoModelFactory):
    class Meta:
        model = Board

    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    color = factory.Faker('hex_color')
    owner = factory.SubFactory(settings.AUTH_USER_MODEL)


class ListFactory(DjangoModelFactory):
    class Meta:
        model = List

    title = factory.Faker('sentence')
    board = factory.SubFactory(BoardFactory)


class CardFactory(DjangoModelFactory):
    class Meta:
        model = Card

    title = factory.Faker('sentence')
    description = factory.Faker('paragraph')
    list = factory.SubFactory(ListFactory)
    priority = factory.Faker('random_int', min=10, max=80)
    due_date = factory.Faker('date_object', end_date='+1y')
    order = factory.Faker('random_int', min=1, max=100)


class MembershipFactory(DjangoModelFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory('apps.accounts.models.User')
    board = factory.SubFactory(BoardFactory)
    role = factory.Faker('random_int', min=10, max=40)
