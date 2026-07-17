from django.db import models


class SignVideo(models.Model):
    """키워드 → 수어 영상.

    영상 파일은 AI 개발 완료 후 AI DB에서 공급될 예정이라, 그때까지 video는 비어 있고
    프론트가 emoji 카드로 대체 표시합니다.
    """

    keyword = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=50)
    # 농인 화면은 텍스트보다 이모지를 1차 신호로 씁니다.
    emoji = models.CharField(max_length=8, default='🖐️')
    # 명세 7.2: 출력 형식은 MP4/H.264
    video = models.FileField(upload_to='sign_videos/', blank=True, null=True)
    # 외부(AI DB 등)에 있는 영상을 가리킬 때 씁니다.
    external_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.emoji} {self.title}'


class QuickKeyword(models.Model):
    """빠른 키워드. 농인이 자주 고르는 순서대로 노출합니다."""

    sign_video = models.ForeignKey(
        SignVideo,
        on_delete=models.CASCADE,
        related_name='quick_keywords',
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f'{self.position}. {self.sign_video}'
