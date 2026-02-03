from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('assessment_core.urls')),
    path('api/iam/', include(('iam.api.urls', 'iam'), namespace='iam')),
]
