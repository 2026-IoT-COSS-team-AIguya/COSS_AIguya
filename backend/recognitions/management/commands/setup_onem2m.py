"""COSS 플랫폼에 AE와 Container를 만듭니다 (28.3 / 28.6 준비).

    python manage.py setup_onem2m

이미 있으면 건너뛰므로 여러 번 돌려도 안전합니다.
AE 생성 응답의 aei 값을 .env의 ONEM2M_ORIGINATOR에 넣어야 이후 요청이 통합니다.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from project.errors import ErrorCode, OneM2MError
from recognitions import onem2m


class Command(BaseCommand):
    help = 'oneM2M AE와 Container를 생성합니다.'

    def handle(self, *args, **options):
        if not onem2m.is_configured():
            self.stderr.write(
                self.style.ERROR(
                    'ONEM2M_BASE_URL / ONEM2M_AE_NAME 이 .env에 없습니다.'
                )
            )
            return

        self.stdout.write(f'플랫폼: {settings.ONEM2M_BASE_URL}/{settings.ONEM2M_CSE_NAME}')
        self.stdout.write(f'AE: {settings.ONEM2M_AE_NAME}')

        # --- AE ---
        try:
            result = onem2m.create_ae()
            aei = result['m2m:ae']['aei']
            self.stdout.write(self.style.SUCCESS(f'AE 생성 완료: aei={aei}'))
            self.stdout.write(
                self.style.WARNING(f'.env 의 ONEM2M_ORIGINATOR={aei} 로 맞춰주세요.')
            )
        except OneM2MError as exc:
            if exc.code == ErrorCode.ONEM2M_DUPLICATE_RESOURCE:
                self.stdout.write('AE 이미 있음 (건너뜀)')
            else:
                self.stderr.write(self.style.ERROR(f'AE 생성 실패: {exc}'))
                return

        # --- Container ---
        for name in (
            onem2m.CONTAINER_VIDEO_METADATA,
            onem2m.CONTAINER_RECOGNITION_RESULTS,
        ):
            try:
                onem2m.create_container(name)
                self.stdout.write(self.style.SUCCESS(f'Container 생성 완료: {name}'))
            except OneM2MError as exc:
                if exc.code == ErrorCode.ONEM2M_DUPLICATE_RESOURCE:
                    self.stdout.write(f'Container 이미 있음 (건너뜀): {name}')
                else:
                    self.stderr.write(self.style.ERROR(f'{name} 생성 실패: {exc}'))

        self.stdout.write(self.style.SUCCESS('완료.'))
