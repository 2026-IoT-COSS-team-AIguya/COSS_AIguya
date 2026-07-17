"""URL configuration for project project.

프론트가 이미 이 경로에 붙어 있습니다 (frontend/lib/api/endpoints.ts).
Django 관례대로 끝에 슬래시를 붙입니다.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('project.api_urls')),
]

# 업로드된 수어 영상을 개발 서버가 서빙합니다.
# (운영에서는 웹서버나 Object Storage가 맡습니다.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
