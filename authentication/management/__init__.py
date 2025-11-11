from django.core.management.base import BaseCommand
from authentication.models import User, Job
from django.utils import timezone
from datetime import timedelta
import random

class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')
        
        # Create users for each role
        roles_data = [
            ('super_admin', 'Super', 'Admin', 'superadmin@example.com', '9999999999', True),
            ('admin', 'Admin', 'User', 'admin@example.com', '9999999998', True),
            ('manager', 'Manager', 'User', 'manager@example.com', '9999999997', True),
            ('marketing', 'Marketing', 'Agent1', 'marketing1@example.com', '9999999996', True),
            ('marketing', 'Marketing', 'Agent2', 'marketing2@example.com', '9999999995', True),
            ('allocater', 'Allocater', 'User', 'allocater@example.com', '9999999994', True),
            ('writer', 'Writer', '1', 'writer1@example.com', '9999999993', True),
            ('writer', 'Writer', '2', 'writer2@example.com', '9999999992', True),
            ('writer', 'Writer', '3', 'writer3@example.com', '9999999991', True),
            ('process_team', 'Process', 'Member', 'process@example.com', '9999999990', True),
            ('accounts', 'Finance', 'Manager', 'accounts@example.com', '9999999989', True),
        ]
        
        created_users = {}
        for role, first, last, email, phone, approved in roles_data:
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password='password123',
                    first_name=f"{first} {last}",
                    phone_number=phone,
                    role=role,
                    is_approved=approved
                )
                created_users[role] = user
                self.stdout.write(self.style.SUCCESS(f'Created {role}: {email}'))
        
        # Create sample jobs
        if 'marketing' in created_users and 'writer' in created_users:
            topics = [
                'Impact of Climate Change on Global Economy',
                'Machine Learning in Healthcare',
                'Sustainable Urban Development',
                'Blockchain Technology Applications',
                'Artificial Intelligence Ethics'
            ]
            
            marketing_user = User.objects.filter(role='marketing').first()
            writer_user = User.objects.filter(role='writer').first()
            
            for i, topic in enumerate(topics):
                job = Job.objects.create(
                    job_id=f'JOB-TEST-{i+1:03d}',
                    created_by=marketing_user,
                    allocated_to=writer_user if i % 2 == 0 else None,
                    topic=topic,
                    word_count=random.randint(1000, 5000),
                    referencing_style=random.choice(['APA', 'Harvard', 'MLA', 'Chicago']),
                    writing_style=random.choice(['Academic', 'Professional', 'Technical']),
                    instruction=f'Please write a comprehensive analysis on {topic}. Include introduction, literature review, methodology, findings, and conclusion.',
                    expected_deadline=timezone.now() + timedelta(days=random.randint(5, 15)),
                    strict_deadline=timezone.now() + timedelta(days=random.randint(3, 10)),
                    value=random.uniform(50, 500),
                    status=random.choice(['drop', 'allocated', 'process'])
                )
                self.stdout.write(self.style.SUCCESS(f'Created job: {job.job_id}'))
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('=' * 60)
        self.stdout.write('LOGIN CREDENTIALS:')
        self.stdout.write('=' * 60)
        for role, first, last, email, phone, approved in roles_data:
            self.stdout.write(f'{role.upper()}: {email} / password123')
        self.stdout.write('=' * 60)