from rest_framework import serializers

from sign_videos.models import QuickKeyword, SignVideo


class SignVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = SignVideo
        fields = ['id', 'keyword', 'title', 'emoji', 'video_url']

    def get_video_url(self, obj):
        """명세 7.2: 백엔드는 절대 URL을 반환합니다.

        영상이 아직 없으면 null을 주고, 프론트가 이모지 카드로 대체 표시합니다.
        """
        if obj.external_url:
            return obj.external_url

        if not obj.video:
            return None

        request = self.context.get('request')
        url = obj.video.url
        return request.build_absolute_uri(url) if request else url


class SignVideoSequenceItemSerializer(serializers.Serializer):
    """명세 7.2: 재생 순서는 position으로 전달합니다."""

    position = serializers.IntegerField()
    sign_video = SignVideoSerializer()


class QuickKeywordSerializer(serializers.ModelSerializer):
    keyword = serializers.CharField(source='sign_video.keyword', read_only=True)
    emoji = serializers.CharField(source='sign_video.emoji', read_only=True)

    class Meta:
        model = QuickKeyword
        fields = ['id', 'keyword', 'emoji', 'position']


class SignVideoSequencePreviewSerializer(serializers.Serializer):
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=False,
    )


class SentenceToSequenceSerializer(serializers.Serializer):
    """자유 문장 입력. 쉼표로 끊지 않고 그냥 문장을 씁니다."""

    sentence = serializers.CharField(max_length=500, trim_whitespace=True)
