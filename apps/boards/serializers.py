from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from .models import Board, List, Card, Membership


class MembershipInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "role",
            "is_active",
            "can_edit",
            "can_comment",
            "can_invite",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BoardSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    memberships = MembershipInlineSerializer(source="memberships.all", many=True, read_only=True)

    class Meta:
        model = Board
        fields = [
            "id",
            "owner",
            "color",
            "title",
            "description",
            "created_at",
            "updated_at",
            "memberships",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at", "memberships"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.method == "POST":
            owner = request.user
            max_boards = getattr(settings, "MAX_BOARDS_PER_USER", 10)
            # Use .count() for DB-level count per guardrails
            boards_count = Board.objects.filter(owner=owner).count()
            if boards_count >= max_boards:
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "Board limit reached for this user.",  # Keep messages in English per user's request
                    ]
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        board = Board.objects.create(owner=user, **validated_data)
        # Ensure owner membership exists with ROLE_OWNER
        Membership.objects.create(
            user=user,
            board=board,
            role=Membership.ROLE_OWNER,
            can_edit=True,
            can_comment=True,
            can_invite=True,
        )
        return board


class ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = List
        fields = [
            "id",
            "title",
            "board",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_board(self, board: Board):
        request = self.context.get("request")
        user = request.user if request else None
        # Ensure the user is at least a member of the board
        is_member = Membership.objects.filter(user=user, board=board, is_active=True).exists()
        if not is_member:
            raise serializers.ValidationError("You are not a member of this board.")
        return board


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = [
            "id",
            "title",
            "description",
            "assignee",
            "list",
            "priority",
            "due_date",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        target_list: List = attrs.get("list") or getattr(self.instance, "list", None)
        assignee = attrs.get("assignee", None)

        if target_list is None:
            return attrs

        # Guard: user must be member of the board owning this list
        board = target_list.board
        if not Membership.objects.filter(user=user, board=board, is_active=True).exists():
            raise serializers.ValidationError("You are not a member of this board.")

        # Guard: assignee (if any) must be a member of the same board
        if assignee and not Membership.objects.filter(user=assignee, board=board, is_active=True).exists():
            raise serializers.ValidationError("Assignee must be a member of the board.")

        return attrs


