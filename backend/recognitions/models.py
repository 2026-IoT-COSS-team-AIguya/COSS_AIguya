from django.conf import settings
from django.db import models


class TranslationStatus(models.TextChoices):
    """명세 6장: 프론트, 프-백, 인-백이 공통으로 사용하는 AI 처리 상태.

    양쪽 백엔드가 동일한 Enum을 써야 합니다 (명세 20장 체크리스트).
    """

    PENDING = 'PENDING', '분석을 준비하고 있어요'
    PROCESSING = 'PROCESSING', '수어를 분석하고 있어요'
    COMPLETED = 'COMPLETED', '분석이 완료되었어요'
    FAILED = 'FAILED', '수어를 인식하지 못했어요'


class SignTranslation(models.Model):
    """수어 영상 한 건의 인식 작업.

    명세 20장: 인-백 연동 식별자는 translation_id(= 이 모델의 pk)로 통일합니다.
    """

    # 번역기 모드(대면)는 대화방 없이 그 자리에서 번역만 합니다.
    # 채팅 모드에서 올라온 건만 conversation이 붙고, 결과가 Message로 연결됩니다.
    conversation = models.ForeignKey(
        'conversations.Conversation',
        on_delete=models.CASCADE,
        related_name='sign_translations',
        null=True,
        blank=True,
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sign_translations',
    )

    # 명세 7.1: 업로드 필드명은 input_video
    input_video = models.FileField(upload_to='sign_inputs/%Y/%m/%d/')

    status = models.CharField(
        max_length=20,
        choices=TranslationStatus.choices,
        default=TranslationStatus.PENDING,
        db_index=True,
    )

    # 라즈베리파이가 보내는 식별자 (26.1 DUPLICATE_CAPTURE_ID).
    # 브라우저 촬영(폴백 경로)에서는 비어 있습니다.
    capture_id = models.CharField(max_length=100, blank=True, db_index=True)
    device_id = models.CharField(max_length=100, blank=True)

    # 27장: 인식 실패와 서버 장애를 구분해야 하므로 코드를 남깁니다.
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)

    model_version = models.CharField(max_length=50, blank=True)
    processing_ms = models.PositiveIntegerField(null=True, blank=True)

    # 30장: oneM2M 등록은 곁가지입니다. 실패해도 영상과 AI 결과는 지우지 않고,
    # 여기에 실패 사실만 남겨 나중에 재시도할 수 있게 합니다 (27장 원칙).
    onem2m_video_registered = models.BooleanField(default=False)
    onem2m_result_registered = models.BooleanField(default=False)
    onem2m_last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            # 명세 27장: 동일한 capture_id가 중복 처리되지 않도록 합니다.
            # 빈 문자열(브라우저 촬영)은 제약에서 빼야 여러 건을 올릴 수 있습니다.
            models.UniqueConstraint(
                fields=['capture_id'],
                condition=~models.Q(capture_id=''),
                name='unique_capture_id',
            ),
        ]

    def __str__(self):
        return f'SignTranslation #{self.pk} ({self.status})'

    @property
    def is_settled(self):
        return self.status in (TranslationStatus.COMPLETED, TranslationStatus.FAILED)


class RecognizedKeyword(models.Model):
    """인식된 키워드 하나. 명세 5.2의 recognized_keywords 항목."""

    translation = models.ForeignKey(
        SignTranslation,
        on_delete=models.CASCADE,
        related_name='recognized_keywords',
    )
    keyword = models.CharField(max_length=50)
    confidence = models.FloatField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']
        constraints = [
            models.UniqueConstraint(
                fields=['translation', 'position'],
                name='unique_keyword_position',
            ),
        ]

    def __str__(self):
        return f'{self.position}. {self.keyword} ({self.confidence:.2f})'


class SentenceCandidate(models.Model):
    """문장 후보.

    명세 5.2의 응답은 문자열 배열이지만, 28.5의 AI 응답 예시는 score를 함께 줍니다.
    score를 보관해 두고 직렬화할 때 문장만 꺼내면 계약을 지키면서 정보도 남습니다.
    """

    translation = models.ForeignKey(
        SignTranslation,
        on_delete=models.CASCADE,
        related_name='sentence_candidates',
    )
    sentence = models.CharField(max_length=200)
    score = models.FloatField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return self.sentence
