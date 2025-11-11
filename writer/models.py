from django.db import models
from django.contrib.auth.models import User

class Job(models.Model):
    # ... existing fields ...
    is_read = models.BooleanField(default=False)  # Add this field
    allocated_at = models.DateTimeField(null=True, blank=True)  # If not exists
    
    # ... rest of your model ...