from rest_framework import serializers

from recognitions.models import RecognizedKeyword, SignTranslation


class RecognizedKeywordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecognizedKeyword
        fields = ['keyword', 'confidence', 'position']


class SignTranslationDetailSerializer(serializers.ModelSerializer):
    """명세 5.2의 처리 완료 / 실패 응답 형식."""

    recognized_keywords = RecognizedKeywordSerializer(many=True, read_only=True)
    sentence_candidates = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()

    class Meta:
        model = SignTranslation
        fields = [
            'id',
            'status',
            'created_at',
            'recognized_keywords',
            'sentence_candidates',
            'error',
        ]

    def get_sentence_candidates(self, obj):
        # 명세는 문자열 배열입니다. score는 DB에만 두고 계약은 그대로 지킵니다.
        return [item.sentence for item in obj.sentence_candidates.all()]

    def get_error(self, obj):
        """명세 9장: 인식 실패는 HTTP 오류가 아니라 이 필드로 전달합니다."""
        if not obj.error_code:
            return None

        return {'code': obj.error_code, 'message': obj.error_message}


class SignTranslationCreatedSerializer(serializers.ModelSerializer):
    """명세 5.2의 업로드 직후(202) 응답."""

    class Meta:
        model = SignTranslation
        fields = ['id', 'status', 'created_at']


class SignTranslationCreateSerializer(serializers.Serializer):
    """명세 20장 체크리스트: 파일 크기와 MIME 타입을 여기서 검증합니다."""

    # 명세 7.1: 업로드 필드명은 input_video
    input_video = serializers.FileField()
    # 번역기 모드(대면)는 대화방 없이 촬영하므로 비워둘 수 있습니다.
    conversation_id = serializers.IntegerField(required=False, allow_null=True)

    # 라즈베리파이가 보내는 식별자. 브라우저 촬영(폴백)에서는 생략됩니다.
    capture_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    device_id = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # 명세 7.1
    ALLOWED_TYPES = ('video/mp4', 'video/webm')
    MAX_BYTES = 50 * 1024 * 1024  # 50MB

    def validate_input_video(self, value):
        # "video/webm;codecs=vp9"처럼 파라미터가 붙어 오므로 앞부분만 봅니다.
        content_type = (value.content_type or '').split(';')[0].strip()

        if content_type not in self.ALLOWED_TYPES:
            # 415는 뷰에서 상태 코드를 붙입니다. 여기서는 코드만 실어 보냅니다.
            raise serializers.ValidationError('unsupported_video_type')

        if value.size > self.MAX_BYTES:
            raise serializers.ValidationError('video_too_large')

        return value


class SignTranslationResultSerializer(serializers.Serializer):
    """인-백이 콜백으로 보내는 결과.

    27장 원칙: AI 응답 JSON은 저장 전에 검증합니다.
    28.5의 AI 응답 예시 형태를 그대로 받습니다.
    """

    class KeywordSerializer(serializers.Serializer):
        keyword = serializers.CharField(max_length=50)
        confidence = serializers.FloatField(min_value=0.0, max_value=1.0)

    class SentenceSerializer(serializers.Serializer):
        sentence = serializers.CharField(max_length=200)
        score = serializers.FloatField(required=False, allow_null=True)

    status = serializers.ChoiceField(choices=['COMPLETED', 'FAILED'])
    keywords = KeywordSerializer(many=True, required=False, default=list)
    sentence_candidates = SentenceSerializer(many=True, required=False, default=list)
    model_version = serializers.CharField(max_length=50, required=False, allow_blank=True)
    processing_ms = serializers.IntegerField(required=False, allow_null=True)
    error = serializers.DictField(required=False, allow_null=True)
