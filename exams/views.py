from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Sum
from django.contrib import messages
import json, random
from .models import Exam, Question, Subject, ExamAttempt, Answer
from accounts.models import User

def role_required(role):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role != role and not (role == 'teacher' and request.user.role == 'admin'):
                return redirect('dashboard')
            return f(request, *args, **kwargs)
        return wrapped
    return decorator

# ─── ADMIN ───────────────────────────────────────────────
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    ctx = {
        'total_users': User.objects.count(),
        'total_students': User.objects.filter(role='student').count(),
        'total_teachers': User.objects.filter(role='teacher').count(),
        'total_exams': Exam.objects.count(),
        'total_attempts': ExamAttempt.objects.filter(is_submitted=True).count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_exams': Exam.objects.order_by('-start_time')[:5],
        'recent_results': ExamAttempt.objects.filter(is_submitted=True).order_by('-submitted_at')[:10],
    }
    return render(request, 'exams/admin_dashboard.html', ctx)

@login_required
def manage_users(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'exams/manage_users.html', {'users': users})

@login_required
def toggle_user(request, user_id):
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Forbidden'}, status=403)
    user = get_object_or_404(User, id=user_id)
    if user != request.user:
        user.is_active = not user.is_active
        user.save()
    return JsonResponse({'active': user.is_active})

@login_required
def all_results(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    results = ExamAttempt.objects.filter(is_submitted=True).select_related('student','exam').order_by('-submitted_at')
    return render(request, 'exams/all_results.html', {'results': results})

# ─── TEACHER ─────────────────────────────────────────────
@login_required
def teacher_dashboard(request):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    exams = Exam.objects.filter(created_by=request.user).annotate(attempt_count=Count('attempts'))
    subjects = Subject.objects.filter(created_by=request.user)
    ctx = {
        'exams': exams,
        'subjects': subjects,
        'total_questions': Question.objects.filter(created_by=request.user).count(),
        'total_attempts': ExamAttempt.objects.filter(exam__created_by=request.user, is_submitted=True).count(),
    }
    return render(request, 'exams/teacher_dashboard.html', ctx)

@login_required
def create_subject(request):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    if request.method == 'POST':
        Subject.objects.create(name=request.POST['name'], code=request.POST['code'], created_by=request.user)
        messages.success(request, 'Subject created!')
        return redirect('teacher_dashboard')
    return render(request, 'exams/create_subject.html')

@login_required
def create_question(request):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    subjects = Subject.objects.filter(created_by=request.user)
    if request.method == 'POST':
        q = Question.objects.create(
            subject_id=request.POST['subject'],
            text=request.POST['text'],
            option_a=request.POST['option_a'],
            option_b=request.POST['option_b'],
            option_c=request.POST['option_c'],
            option_d=request.POST['option_d'],
            correct_answer=request.POST['correct_answer'],
            marks=int(request.POST.get('marks', 1)),
            difficulty=request.POST.get('difficulty', 'medium'),
            created_by=request.user
        )
        messages.success(request, 'Question added!')
        return redirect('question_bank')
    return render(request, 'exams/create_question.html', {'subjects': subjects})

@login_required
def question_bank(request):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    questions = Question.objects.filter(created_by=request.user).select_related('subject')
    return render(request, 'exams/question_bank.html', {'questions': questions})

@login_required
def delete_question(request, q_id):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    q = get_object_or_404(Question, id=q_id, created_by=request.user)
    q.delete()
    messages.success(request, 'Question deleted.')
    return redirect('question_bank')

@login_required
def create_exam(request):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    subjects = Subject.objects.filter(created_by=request.user)
    if request.method == 'POST':
        import datetime

        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')

        start_naive = datetime.datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
        end_naive = datetime.datetime.strptime(end_str, '%Y-%m-%dT%H:%M')

        IST_OFFSET = datetime.timedelta(hours=5, minutes=30)
        start_time = (start_naive - IST_OFFSET).replace(tzinfo=datetime.timezone.utc)
        end_time = (end_naive - IST_OFFSET).replace(tzinfo=datetime.timezone.utc)

        exam = Exam.objects.create(
            title=request.POST['title'],
            subject_id=request.POST['subject'],
            description=request.POST.get('description', ''),
            duration_minutes=int(request.POST.get('duration', 60)),
            pass_marks=int(request.POST.get('pass_marks', 0)),
            start_time=start_time,
            end_time=end_time,
            created_by=request.user,
            shuffle_questions=bool(request.POST.get('shuffle', False)),
            is_active=True,
        )
        q_ids = request.POST.getlist('questions')
        questions = Question.objects.filter(id__in=q_ids)
        exam.questions.set(questions)
        exam.total_marks = sum(q.marks for q in questions)
        exam.save()
        messages.success(request, 'Exam created!')
        return redirect('teacher_dashboard')
    questions = Question.objects.filter(created_by=request.user)
    return render(request, 'exams/create_exam.html', {'subjects': subjects, 'questions': questions})

@login_required
def exam_results(request, exam_id):
    if request.user.role not in ('teacher', 'admin'):
        return redirect('dashboard')
    exam = get_object_or_404(Exam, id=exam_id)
    attempts = ExamAttempt.objects.filter(exam=exam, is_submitted=True).select_related('student')
    avg = attempts.aggregate(Avg('score'))['score__avg'] or 0
    passed = attempts.filter(score__gte=exam.pass_marks).count()
    ctx = {'exam': exam, 'attempts': attempts, 'avg_score': round(avg, 1), 'passed_count': passed}
    return render(request, 'exams/exam_results.html', ctx)

# ─── STUDENT ─────────────────────────────────────────────
@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    now = timezone.now()
    available_exams = Exam.objects.filter(is_active=True, start_time__lte=now, end_time__gte=now)
    my_attempts = ExamAttempt.objects.filter(student=request.user, is_submitted=True).select_related('exam')
    attempted_ids = my_attempts.values_list('exam_id', flat=True)
    upcoming = Exam.objects.filter(is_active=True, start_time__gt=now)
    ctx = {
        'available_exams': available_exams,
        'attempted_ids': list(attempted_ids),
        'my_attempts': my_attempts.order_by('-submitted_at')[:5],
        'upcoming_exams': upcoming,
        'total_attempted': my_attempts.count(),
        'total_passed': sum(1 for a in my_attempts if a.passed),
        'avg_score': round(my_attempts.aggregate(Avg('score'))['score__avg'] or 0, 1),
    }
    return render(request, 'exams/student_dashboard.html', ctx)

@login_required
def start_exam(request, exam_id):
    if request.user.role != 'student':
        return redirect('dashboard')
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    now = timezone.now()
    if now < exam.start_time or now > exam.end_time:
        messages.error(request, 'Exam is not available now.')
        return redirect('student_dashboard')
    attempt, created = ExamAttempt.objects.get_or_create(exam=exam, student=request.user)
    if attempt.is_submitted:
        return redirect('exam_result_detail', attempt_id=attempt.id)
    questions = list(exam.questions.all())
    if exam.shuffle_questions:
        random.shuffle(questions)
    return render(request, 'exams/take_exam.html', {'exam': exam, 'attempt': attempt, 'questions': questions})

@login_required
def submit_exam(request, exam_id):
    if request.method != 'POST':
        return redirect('student_dashboard')
    exam = get_object_or_404(Exam, id=exam_id)
    attempt = get_object_or_404(ExamAttempt, exam=exam, student=request.user, is_submitted=False)
    data = json.loads(request.body)
    answers_data = data.get('answers', {})
    time_taken = data.get('time_taken', 0)
    score = 0
    Answer.objects.filter(attempt=attempt).delete()
    for question in exam.questions.all():
        selected = answers_data.get(str(question.id), '')
        is_correct = selected == question.correct_answer
        marks = question.marks if is_correct else 0
        score += marks
        Answer.objects.create(attempt=attempt, question=question,
            selected_option=selected, is_correct=is_correct, marks_obtained=marks)
    attempt.score = score
    attempt.total_marks = exam.total_marks
    attempt.is_submitted = True
    attempt.submitted_at = timezone.now()
    attempt.time_taken = time_taken
    attempt.save()
    return JsonResponse({'success': True, 'score': score, 'total': exam.total_marks,
        'percentage': attempt.percentage, 'passed': attempt.passed, 'attempt_id': attempt.id})

@login_required
def exam_result_detail(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, id=attempt_id)
    if request.user.role == 'student' and attempt.student != request.user:
        return redirect('student_dashboard')
    answers = attempt.answers.select_related('question').all()
    return render(request, 'exams/result_detail.html', {'attempt': attempt, 'answers': answers})

@login_required
def my_results(request):
    if request.user.role != 'student':
        return redirect('dashboard')
    attempts = ExamAttempt.objects.filter(student=request.user, is_submitted=True).select_related('exam').order_by('-submitted_at')
    return render(request, 'exams/my_results.html', {'attempts': attempts})



