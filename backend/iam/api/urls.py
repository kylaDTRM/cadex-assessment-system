from django.urls import path
from .views import TokenIssueView
from iam.api.views_policy import TenantPolicyListCreate, TenantPolicyDeploy

urlpatterns = [
    path('token/', TokenIssueView.as_view(), name='iam-token'),
    path('policies/', TenantPolicyListCreate.as_view(), name='tenantpolicy-list-create'),
    path('policies/<uuid:pk>/deploy/', TenantPolicyDeploy.as_view(), name='tenantpolicy-deploy'),
]
