from django.urls import path
from .views import TokenIssueView

urlpatterns = [
    path('token/', TokenIssueView.as_view(), name='iam-token'),
]
