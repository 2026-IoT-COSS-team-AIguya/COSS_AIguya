"""쓰기와 외부 연동 (명세 20장 체크리스트)."""

import logging
import threading
import time
from urllib.parse import urljoin

from django.conf import settings
from django.db import close_old_connections, transaction
from rest_framework import status

from conversations.models import Conversation
from conversations.services import check_conversation_access, create_translation_message
from project.errors import ApiError, ErrorCode, OneM2MError
from recognitions import ai_client, onem2m
from recognitions.models import (
    CaptureTarget,
    RecognizedKeyword,
    SentenceCandidate,
    SignTranslation,
    TranslationStatus,
)
from recognitions.serializers import SignTranslationResultSerializer

logger = logging.getLogger(__name__)

# 이 아래로 떨어지면 인식은 됐지만 못 믿겠다고 봅니다 (26.2 LOW_CONFIDENCE).
MIN_CONFIDENCE = 0.5


def set_capture_target(user, conversation_id):
    """이 사용자가 지금 촬영하면 결과가 어디로 갈지 등록합니다.

    conversation_id가 None이면 번역기 모드(대면)입니다.
    화면을 옮길 때마다 프론트가 호출합니다.
    """
    conversation = None

    if conversation_id:
        conversation = Conversation.objects.filter(pk=conversation_id).first()

        if conversation is None:
            raise ApiError(
                ErrorCode.CONVERSATION_NOT_FOUND,
                '대화를 찾을 수 없습니다.',
                status.HTTP_404_NOT_FOUND,
            )

        # 남의 대화방을 촬영 대상으로 걸어두지 못하게 합니다.
        check_conversation_access(conversation, user)

    target, _ = CaptureTarget.objects.update_or_create(
        user=user,
        defaults={'conversation': conversation},
    )
    return target


def resolve_capture_target(user):
    """등록된 촬영 대상의 대화방. 번역기 모드거나 등록 전이면 None."""
    target = CaptureTarget.objects.filter(user=user).select_related('conversation').first()

    if target is None:
        return None

    # 대화방이 삭제되면 on_delete=SET_NULL로 null이 됩니다 — 번역기 모드로 떨어집니다.
    return target.conversation


def create_sign_translation(user, conversation_id, input_video, capture_id='', device_id=''):
    conversation = None

    if conversation_id:
        conversation = Conversation.objects.filter(pk=conversation_id).first()

        if conversation is None:
            raise ApiError(
                ErrorCode.CONVERSATION_NOT_FOUND,
                '대화를 찾을 수 없습니다.',
                status.HTTP_404_NOT_FOUND,
            )

        check_conversation_access(conversation, user)
    else:
        # 업로더가 목적지를 지정하지 않았습니다 — 라즈베리파이는 물리 버튼만 보고
        # 촬영하므로 사용자가 어느 화면을 보고 있는지 알 수 없습니다. 대신 화면이
        # 등록해둔 대상을 여기서 읽습니다. 등록 전이면 None → 번역기 모드입니다.
        conversation = resolve_capture_target(user)

        # 등록해둔 사이에 대화방에서 나갔을 수 있습니다. 그대로 올리면 권한 없는
        # 방에 메시지가 생기므로, 조용히 번역기 모드로 되돌립니다.
        if conversation is not None:
            try:
                check_conversation_access(conversation, user)
            except ApiError:
                logger.info(
                    '촬영 대상 대화 %s 접근 불가 — 번역기 모드로 전환 (user=%s)',
                    conversation.id,
                    user.id,
                )
                conversation = None

    # 27장: 동일한 capture_id가 중복 처리되지 않도록 합니다.
    if capture_id and SignTranslation.objects.filter(capture_id=capture_id).exists():
        raise ApiError(
            ErrorCode.DUPLICATE_CAPTURE_ID,
            '이미 처리된 촬영입니다.',
            status.HTTP_409_CONFLICT,
        )

    try:
        translation = SignTranslation.objects.create(
            conversation=conversation,
            requester=user,
            input_video=input_video,
            capture_id=capture_id or '',
            device_id=device_id or '',
        )
    except OSError as exc:
        logger.exception('영상 저장 실패')
        raise ApiError(
            ErrorCode.VIDEO_SAVE_FAILED,
            '영상을 저장하지 못했습니다.',
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    return translation


def build_video_url(translation, request=None):
    """30장: oneM2M과 인-백에 넘길 영상 URL.

    29장 13번(외부에서 접근 가능해야 하는가)이 미확정이라, 지금은 개발 서버가
    서빙하는 media URL을 씁니다.
    """
    url = translation.input_video.url

    if settings.MEDIA_PUBLIC_BASE_URL:
        return urljoin(
            settings.MEDIA_PUBLIC_BASE_URL.rstrip('/') + '/',
            url.lstrip('/'),
        )

    if request is not None:
        return request.build_absolute_uri(url)

    return url


def set_translation_processing(translation_id):
    SignTranslation.objects.filter(
        pk=translation_id, status=TranslationStatus.PENDING
    ).update(status=TranslationStatus.PROCESSING)


def _claim(translation, new_status):
    """아직 확정되지 않은 건을 원자적으로 선점합니다.

    명세 20장: 콜백을 중복 수신해도 결과가 중복 저장되면 안 됩니다.
    파이썬에서 is_settled를 확인한 뒤 쓰면 그 사이에 다른 스레드(백그라운드
    파이프라인 / 인-백 콜백)가 끼어들어 키워드가 두 번 들어갑니다.
    조건부 UPDATE 한 방으로 경쟁에서 이긴 쪽만 진행하게 합니다.

    이긴 경우 True를 돌려줍니다.
    """
    claimed = (
        SignTranslation.objects.filter(pk=translation.pk)
        .exclude(status__in=[TranslationStatus.COMPLETED, TranslationStatus.FAILED])
        .update(status=new_status)
    )
    return claimed == 1


def set_translation_failed(translation, code, message):
    # 이미 확정된 결과는 덮지 않습니다.
    if not _claim(translation, TranslationStatus.FAILED):
        translation.refresh_from_db()
        return translation

    translation.status = TranslationStatus.FAILED
    translation.error_code = code
    translation.error_message = message
    translation.save(update_fields=['error_code', 'error_message'])
    return translation


@transaction.atomic
def set_translation_completed(translation, payload):
    """검증된 AI 결과를 저장하고 대화에 메시지로 올립니다."""
    keywords = payload.get('keywords', [])

    # 인식 실패 / 낮은 신뢰도는 아래에서 set_translation_failed가 선점을 맡습니다.
    # 여기서 미리 선점하면 실패 경로가 두 번 선점을 시도하게 됩니다.

    # 27장: 인식 실패와 서버 장애를 구분합니다. 빈 결과는 장애가 아니라 인식 실패입니다.
    if not keywords:
        return set_translation_failed(
            translation,
            ErrorCode.SIGN_NOT_DETECTED,
            '영상에서 수어 동작을 찾지 못했습니다.',
        )

    # 26.2 LOW_CONFIDENCE — 인식은 했지만 신뢰도가 너무 낮은 경우.
    if all(item['confidence'] < MIN_CONFIDENCE for item in keywords):
        return set_translation_failed(
            translation,
            ErrorCode.LOW_CONFIDENCE,
            '수어를 또렷하게 인식하지 못했습니다.',
        )

    # 여기서부터 실제로 씁니다. 선점에 실패했다면 다른 쪽(백그라운드 파이프라인 또는
    # 인-백 콜백)이 이미 저장했다는 뜻이므로 그대로 물러납니다.
    if not _claim(translation, TranslationStatus.COMPLETED):
        translation.refresh_from_db()
        return translation

    RecognizedKeyword.objects.bulk_create(
        [
            RecognizedKeyword(
                translation=translation,
                keyword=item['keyword'],
                confidence=item['confidence'],
                position=index + 1,
            )
            for index, item in enumerate(keywords)
        ]
    )

    SentenceCandidate.objects.bulk_create(
        [
            SentenceCandidate(
                translation=translation,
                sentence=item['sentence'],
                score=item.get('score'),
                position=index,
            )
            for index, item in enumerate(payload.get('sentence_candidates', []))
        ]
    )

    # status는 _claim이 이미 COMPLETED로 바꿨습니다. 나머지만 채웁니다.
    translation.status = TranslationStatus.COMPLETED
    translation.error_code = ''
    translation.error_message = ''
    translation.model_version = payload.get('model_version', '')
    translation.processing_ms = payload.get('processing_ms')
    translation.save(
        update_fields=[
            'error_code',
            'error_message',
            'model_version',
            'processing_ms',
        ]
    )

    # 28.8: 채팅 모드에서 올라온 건만 Message로 연결합니다.
    # 번역기 모드(대면)는 대화방이 없고, 번역기 화면이 결과를 직접 폴링합니다.
    if translation.conversation_id:
        create_translation_message(
            translation.conversation,
            translation.requester,
            translation,
        )

    return translation


def save_translation_result(translation, raw_payload):
    """27장: AI 응답 JSON은 저장 전에 검증합니다."""
    serializer = SignTranslationResultSerializer(data=raw_payload)

    if not serializer.is_valid():
        logger.error('AI 응답 검증 실패: %s', serializer.errors)
        return set_translation_failed(
            translation,
            ErrorCode.INVALID_AI_RESPONSE,
            '분석 결과 형식이 올바르지 않습니다.',
        )

    payload = serializer.validated_data

    if payload['status'] == 'FAILED':
        error = payload.get('error') or {}
        return set_translation_failed(
            translation,
            error.get('code', ErrorCode.SIGN_NOT_DETECTED),
            error.get('message', '영상에서 수어 동작을 찾지 못했습니다.'),
        )

    return set_translation_completed(translation, payload)


def _run_pipeline(translation_id, video_url):
    """업로드 접수 후 백그라운드에서 도는 분석 파이프라인.

    Celery 없이 스레드로 돌립니다. 시연 규모에서는 충분하고, 프론트가
    PENDING → PROCESSING → COMPLETED 전이를 실제로 관찰할 수 있습니다.
    (운영에서는 Celery/RQ 같은 작업 큐로 옮겨야 합니다.)
    """
    close_old_connections()

    try:
        set_translation_processing(translation_id)

        translation = SignTranslation.objects.filter(pk=translation_id).first()
        if translation is None:
            return

        if ai_client.is_mock():
            # 가짜 결과가 즉시 돌아오면 상태 전이가 안 보이므로 잠깐 둡니다.
            time.sleep(2)

        try:
            payload = ai_client.predict_sign_keywords(translation, video_url)
        except ApiError as exc:
            # 서버 장애는 인식 실패와 구분해서 기록합니다 (27장).
            logger.warning('AI 호출 실패 (translation=%s): %s', translation_id, exc.code)
            set_translation_failed(translation, exc.code, exc.message)
            return

        translation = save_translation_result(translation, payload)

        # 28.6: AI 완료 후 결과 메타데이터를 등록합니다.
        # 27장: 여기서 실패해도 영상과 AI 결과는 그대로 둡니다.
        _try_register_result(translation)

    except Exception:
        logger.exception('분석 파이프라인 오류 (translation=%s)', translation_id)
    finally:
        close_old_connections()


def _try_register_result(translation):
    try:
        # 설정이 없으면 None이 옵니다. 예외가 아니라고 해서 "등록됨"은 아닙니다 —
        # 실제로 보낸 경우에만 True로 둬야 플래그가 거짓말을 하지 않습니다.
        result = onem2m.register_recognition_result(translation)
        translation.onem2m_result_registered = result is not None
        translation.onem2m_last_error = (
            '' if result is not None else 'oneM2M 미설정 — 등록 건너뜀'
        )
    except OneM2MError as exc:
        # 27장 원칙: oneM2M 전송 실패는 로그에 기록하고 필요 시 재시도합니다.
        logger.warning('oneM2M 결과 등록 실패 (translation=%s): %s', translation.id, exc)
        translation.onem2m_result_registered = False
        translation.onem2m_last_error = str(exc)

    translation.save(
        update_fields=['onem2m_result_registered', 'onem2m_last_error']
    )


def try_register_video_metadata(translation, video_url):
    """28.6: 영상 업로드 후 메타데이터를 등록합니다.

    27장: 실패해도 업로드 자체는 성공으로 둡니다.
    """
    try:
        result = onem2m.register_video_metadata(translation, video_url)
        translation.onem2m_video_registered = result is not None
        translation.onem2m_last_error = (
            '' if result is not None else 'oneM2M 미설정 — 등록 건너뜀'
        )
    except OneM2MError as exc:
        logger.warning('oneM2M 영상 등록 실패 (translation=%s): %s', translation.id, exc)
        translation.onem2m_video_registered = False
        translation.onem2m_last_error = str(exc)

    translation.save(update_fields=['onem2m_video_registered', 'onem2m_last_error'])


def submit_translation_to_ai(translation, video_url):
    """분석을 백그라운드로 넘깁니다. 업로드 응답은 기다리지 않고 202로 돌아갑니다."""
    thread = threading.Thread(
        target=_run_pipeline,
        args=(translation.id, video_url),
        daemon=True,
    )
    thread.start()


def retry_sign_translation(translation, video_url):
    """실패한 건을 같은 id로 다시 돌립니다."""
    translation.status = TranslationStatus.PENDING
    translation.error_code = ''
    translation.error_message = ''
    translation.save(update_fields=['status', 'error_code', 'error_message'])

    translation.recognized_keywords.all().delete()
    translation.sentence_candidates.all().delete()

    submit_translation_to_ai(translation, video_url)
    return translation
