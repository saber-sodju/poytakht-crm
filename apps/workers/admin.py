from django.contrib import admin
from .models import Position, Team, Worker, Attendance, SalaryPayment

admin.site.register(Position)
admin.site.register(Team)
admin.site.register(Worker)
admin.site.register(Attendance)
admin.site.register(SalaryPayment)
