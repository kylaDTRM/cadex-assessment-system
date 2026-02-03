from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('assessment_core.urls')),
    path('api/iam/', include(('iam.api.urls', 'iam'), namespace='iam')),
    path('api/grade-integrity/', include('grade_integrity.urls')),
    path('api/exam-integrity/', include('exam_integrity.urls')),
]
