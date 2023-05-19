from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.views import APIView
from rest_framework import (
    filters,
    permissions,
    status,
    viewsets,
)

from api.v1.filters import TitlesFilter
from api.mixins import ListCreateDestroyViewSet
from api.v1.permissions import ReadOnly, AdminRules, AccessOrReadOnly
from api.v1.serializers import (
    CategorySerializer,
    CommentSerializer,
    GenreSerializer,
    ProfileSerializer,
    ReviewSerializer,
    TitleCreateUpdateSerializer,
    TitleSerializer,
    SignUpSerializer,
    TokenSerializer,
    UserSerializer,
)
from reviews.models import Category, Genre, Review, Title, User


HTTP_METHOD = ('get', 'post', 'patch', 'delete')


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AdminRules,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('username',)
    pagination_class = PageNumberPagination
    http_method_names = HTTP_METHOD
    lookup_field = 'username'

    @action(
        detail=False,
        methods=['get', 'patch'],
        serializer_class=ProfileSerializer,
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request):
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                request.user, data=request.data, partial=True
            )
            try:
                serializer.is_valid(raise_exception=True)
            except ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class SignUPView(APIView):
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        confirmation_code = default_token_generator.make_token(user)
        user.confirmation_code = (
            confirmation_code  # Присвоение значения confirmation_code
        )
        user.save()  # Сохранение пользователя с заполненным confirmation_code
        send_mail(
            subject='Confirmation code',
            message=f'{confirmation_code}',
            from_email=settings.FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TokenView(APIView):
    def post(self, request):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data.get('username')
        confirmation_code = serializer.validated_data.get('confirmation_code')
        user = get_object_or_404(User, username=username)
        if user.confirmation_code == confirmation_code:
            jwt_token = AccessToken.for_user(user)
            return Response(
                {'token': f'{jwt_token}'}, status=status.HTTP_200_OK
            )
        return Response(
            {
                'message': 'Это 400 ошибка, потому что '
                'отсутствует обязательное поле для создания токена '
                'или оно некорректно'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class CategoriesViewSet(ListCreateDestroyViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [ReadOnly | AdminRules]
    pagination_class = PageNumberPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('name',)
    lookup_field = 'slug'
    ordering = ('id',)


class GenresViewSet(ListCreateDestroyViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [ReadOnly | AdminRules]
    lookup_field = 'slug'
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ('name',)
    ordering = ('id',)


class TitlesViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.annotate(Avg('reviews__score'))
    serializer_class = TitleSerializer
    permission_classes = [ReadOnly | AdminRules]
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    http_method_names = HTTP_METHOD
    filterset_class = TitlesFilter
    ordering = ('id',)

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return TitleCreateUpdateSerializer
        return TitleSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        AccessOrReadOnly,
    )
    pagination_class = PageNumberPagination
    http_method_names = HTTP_METHOD
    filter_backends = (filters.OrderingFilter,)
    ordering = ('id',)

    def get_queryset(self):
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        return title.reviews.all()

    def perform_create(self, serializer):
        title = get_object_or_404(Title, id=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        AccessOrReadOnly,
    )
    pagination_class = PageNumberPagination
    http_method_names = HTTP_METHOD
    filter_backends = (filters.OrderingFilter,)
    ordering = ('id',)

    def perform_create(self, serializer):
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title__id=self.kwargs.get('title_id'),
        )
        serializer.save(author=self.request.user, review=review)

    def get_queryset(self):
        review = get_object_or_404(
            Review,
            id=self.kwargs.get('review_id'),
            title__id=self.kwargs.get('title_id'),
        )
        return review.comments.all()
