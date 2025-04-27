from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum

class Task(models.Model):
    # Task status options
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    # ForeignKey to User, assuming the employee is a user
    employee = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='tasks')

    # Task details
    title = models.CharField(max_length=255)
    description = models.TextField()
    hours_spent = models.DecimalField(max_digits=4, decimal_places=2)  # Max 9999.99 hours
    tags = models.CharField(max_length=255, blank=True, null=True)  # Optional tags
    date = models.DateField()  # Date when the task was performed
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    manager_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Task: {self.title} - {self.status} - {self.hours_spent} hours"

    def clean(self):
        """
        Ensure that total logged hours for the employee on the same date
        do not exceed the 8-hour daily limit.
        """
        # Fetch the total hours already logged by the employee on the given date
        total_hours_today = Task.objects.filter(
            employee=self.employee, date=self.date
        ).aggregate(total_hours=Sum('hours_spent'))['total_hours'] or 0

        # If this task is being updated, exclude its previous hours from the total
        if self.pk:
            total_hours_today -= self.hours_spent

        # Ensure that adding this task's hours doesn't exceed the 8-hour daily limit
        if total_hours_today + self.hours_spent > 8:
            raise ValidationError("Total hours for the day cannot exceed 8 hours.")

    def save(self, *args, **kwargs):
        """Override save method to call clean method for validation."""
        self.clean()  # Validate before saving the task
        super().save(*args, **kwargs)

    @classmethod
    def total_hours_for_employee_on_date(cls, employee, date):
        """
        Class method to calculate the total hours worked by an employee on a specific date.
        """
        return cls.objects.filter(employee=employee, date=date).aggregate(
            total_hours=Sum('hours_spent')
        )['total_hours'] or 0
