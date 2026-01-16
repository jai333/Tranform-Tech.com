from django.contrib import admin
from .models import Candidate, Job, Interview, User

# Register your models here.
admin.site.register(Candidate)
admin.site.register(Job)
admin.site.register(Interview)
admin.site.register(User)
