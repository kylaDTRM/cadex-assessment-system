from django.contrib import admin
from .models import User, Institution, Course, Assessment, Question, Attempt, Response

admin.site.register(User)
admin.site.register(Institution)
admin.site.register(Course)
admin.site.register(Assessment)
admin.site.register(Question)
admin.site.register(Attempt)
admin.site.register(Response)
