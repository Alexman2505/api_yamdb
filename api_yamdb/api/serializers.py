import statistics
from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    SerializerMethodField,
    SlugRelatedField,
)

from reviews.models import (
    Category,
    Genre,
    GenreTitle,
    Title,
)


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ('name', 'slug')


class GenreSerializer(ModelSerializer):
    class Meta:
        model = Genre
        fields = ('name', 'slug')


class TitleSerializer(ModelSerializer):
    category = CategorySerializer()
    genre = GenreSerializer(many=True)
    rating = SerializerMethodField()

    class Meta:
        model = Title
        fields = '__all__'

    def get_rating(self, obj):
        scores = []
        for review in obj.reviews.all():
            scores.append(review.score)
        return statistics.mean(scores) if scores else None


class TitleCreateUpdateSerializer(ModelSerializer):
    category = SlugRelatedField(
        queryset=Category.objects.all(), slug_field='slug', required=True
    )
    genre = SlugRelatedField(
        queryset=Genre.objects.all(),
        slug_field='slug',
        many=True,
        required=True,
    )
    description = CharField(required=False)

    class Meta:
        model = Title
        fields = '__all__'
        read_only_fields = ('rating',)

    def create(self, validated_data):
        category = validated_data.pop('category')
        genres = validated_data.pop('genre')
        title = Title.objects.create(**validated_data, category=category)

        for genre in genres:
            genre = Genre.objects.get(slug=genre.slug)
            GenreTitle.objects.create(genre=genre, title=title)
        return title
