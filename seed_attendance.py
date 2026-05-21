import os
import django
import random
from datetime import date, timedelta, datetime
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tracker.settings')
django.setup()

from django.contrib.auth.models import User
from projects.models import Attendance, BreakLog, LeaveRequest, LeaveBalance, ProductivityLog, ActivityLog

def seed_attendance_data():
    print("Starting attendance database seeding...")
    
    # Clean existing attendance data
    Attendance.objects.all().delete()
    BreakLog.objects.all().delete()
    LeaveRequest.objects.all().delete()
    LeaveBalance.objects.all().delete()
    ProductivityLog.objects.all().delete()
    
    # Get staff users
    staff_usernames = ['admin', 'projectmanager', 'teamlead', 'teammember', 'teammember2', 'teammember3', 'teammember4', 'adhi', 'tl1']
    users = User.objects.filter(username__in=staff_usernames)
    
    if not users.exists():
        print("Staff users do not exist. Please run python populate_db.py first!")
        return

    # Seed LeaveBalances first
    for u in users:
        LeaveBalance.objects.get_or_create(
            user=u,
            defaults={
                'sick_balance': random.randint(8, 12),
                'casual_balance': random.randint(10, 15),
                'emergency_balance': random.randint(3, 5),
                'wfh_balance': random.randint(15, 20)
            }
        )

    # Let's seed past 45 days
    today = date.today()
    start_date = today - timedelta(days=45)
    
    moods = ['😊 Happy', '😐 Normal', '😴 Tired', '🔥 Focused']
    locations = ['office', 'remote']
    devices = ['desktop', 'mobile']
    
    work_tasks = [
        "Worked on backend database integration",
        "Refactored navigation components in layout template",
        "Assisted team member with bug resolution",
        "Drafted client prototype specifications",
        "Reviewed pull requests and merged staging branch",
        "Participated in weekly project sync and standup",
        "Optimized slow SQL queries and indexes",
        "Configured security permissions for clients dashboard",
        "Fixed styling compatibility issues in safari"
    ]
    
    blockers_list = [
        "Waiting for API documentation from client team",
        "Struggling with local environment Docker setup",
        "Pending approval on updated project UI designs",
        "Network latency is slowing down cloud deployment test"
    ]

    for u in users:
        print(f"Seeding logs for user: {u.username}")
        current_streak = 0
        
        # Iterate day by day
        for i in range(46):
            curr_date = start_date + timedelta(days=i)
            
            # Skip future dates
            if curr_date > today:
                continue
                
            # Skip weekends (Saturday=5, Sunday=6)
            if curr_date.weekday() >= 5:
                continue

            # Status roll
            roll = random.random()
            
            # 84% present/late, 6% absent, 10% leave/wfh leave
            if roll < 0.84:
                # Present (74%) vs Late (10%)
                is_late = roll < 0.10
                status = 'late' if is_late else 'present'
                current_streak += 1
                
                # Check-in time
                if is_late:
                    # Checked in between 9:16 AM and 10:30 AM
                    hour = random.randint(9, 10)
                    minute = random.randint(16, 59) if hour == 9 else random.randint(0, 30)
                else:
                    # Checked in between 8:30 AM and 9:14 AM
                    hour = 8 if random.random() < 0.4 else 9
                    minute = random.randint(30, 59) if hour == 8 else random.randint(0, 14)
                
                check_in_time = timezone.make_aware(
                    datetime.combine(curr_date, datetime.min.time().replace(hour=hour, minute=minute))
                )
                
                # Check-out time (5:00 PM to 6:45 PM)
                out_hour = random.randint(17, 18)
                out_minute = random.randint(0, 45)
                check_out_time = timezone.make_aware(
                    datetime.combine(curr_date, datetime.min.time().replace(hour=out_hour, minute=out_minute))
                )
                
                location = random.choices(locations, weights=[0.75, 0.25])[0]
                device = random.choices(devices, weights=[0.9, 0.1])[0]
                mood = random.choice(moods)
                
                # Create Attendance
                att = Attendance.objects.create(
                    user=u,
                    date=curr_date,
                    check_in=check_in_time,
                    check_out=check_out_time,
                    status=status,
                    location=location,
                    device=device,
                    mood=mood,
                    streak=current_streak,
                    today_work=random.choice(work_tasks),
                    blockers=random.choice(blockers_list) if random.random() < 0.15 else None,
                    progress=random.randint(40, 100)
                )
                
                # Create Lunch Break (1:00 PM to 1:45 PM approx)
                lunch_start = timezone.make_aware(
                    datetime.combine(curr_date, datetime.min.time().replace(hour=13, minute=random.randint(0, 10)))
                )
                lunch_end = timezone.make_aware(
                    datetime.combine(curr_date, datetime.min.time().replace(hour=13, minute=random.randint(40, 50)))
                )
                
                BreakLog.objects.create(
                    attendance=att,
                    break_type='lunch',
                    start_time=lunch_start,
                    end_time=lunch_end
                )
                
                # Create Tea Break sometimes (4:00 PM to 4:15 PM)
                if random.random() < 0.6:
                    tea_start = timezone.make_aware(
                        datetime.combine(curr_date, datetime.min.time().replace(hour=16, minute=random.randint(0, 5)))
                    )
                    tea_end = timezone.make_aware(
                        datetime.combine(curr_date, datetime.min.time().replace(hour=16, minute=random.randint(15, 20)))
                    )
                    
                    BreakLog.objects.create(
                        attendance=att,
                        break_type='tea',
                        start_time=tea_start,
                        end_time=tea_end
                    )

                # Productivity Log
                focus_sec = int(att.total_work_seconds() * random.uniform(0.78, 0.92))
                ProductivityLog.objects.create(
                    user=u,
                    date=curr_date,
                    focus_time_seconds=focus_sec,
                    efficiency=random.randint(82, 98),
                    tasks_completed=random.randint(1, 5),
                    bugs_fixed=random.randint(0, 3),
                    meetings_attended=random.choice([0, 1, 2])
                )
                
            elif roll < 0.90:
                # Absent
                current_streak = 0
                Attendance.objects.create(
                    user=u,
                    date=curr_date,
                    status='absent'
                )
                
            else:
                # Leave
                current_streak = 0
                
                # Create Leave Request
                leave_types = ['sick', 'casual', 'emergency']
                l_type = random.choice(leave_types)
                
                LeaveRequest.objects.create(
                    user=u,
                    leave_type=l_type,
                    start_date=curr_date,
                    end_date=curr_date,
                    reason=f"Taking {l_type} leave to address personal matters.",
                    status='approved',
                    approved_by=User.objects.filter(profile__role='admin').first() or u
                )
                
                Attendance.objects.create(
                    user=u,
                    date=curr_date,
                    status='leave'
                )

    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_attendance_data()
