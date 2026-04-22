from django.db import models
from django.utils import timezone
from accounts.models import User
from django.core.exceptions import ValidationError

OPTIONS = [
    ('A', 'Option A'),
    ('B', 'Option B'),
    ('C', 'Option C'),
    ('D', 'Option D'),
]

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    DIFFICULTY = [('easy','Easy'), ('medium','Medium'), ('hard','Hard')]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)

    correct_answer = models.CharField(max_length=1, choices=OPTIONS)
    marks = models.IntegerField(default=1)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY, default='medium')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]


class Exam(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    duration_minutes = models.PositiveIntegerField(default=60)
    total_marks = models.IntegerField(default=0)
    pass_marks = models.IntegerField(default=0)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    questions = models.ManyToManyField(Question, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    shuffle_questions = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_live(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    def clean(self):
        if self.pass_marks > self.total_marks:
            raise ValidationError("Pass marks cannot be greater than total marks")


class ExamAttempt(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    score = models.IntegerField(default=0)
    total_marks = models.IntegerField(default=0)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = (('exam', 'student'),)

    @property
    def percentage(self):
        if self.total_marks == 0:
            return 0
        return round((self.score / self.total_marks) * 100, 2)

    @property
    def passed(self):
        return self.score >= self.exam.pass_marks


class Answer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    selected_option = models.CharField(max_length=1, choices=OPTIONS, blank=True)
    is_correct = models.BooleanField(default=False)
    marks_obtained = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.selected_option == self.question.correct_answer:
            self.is_correct = True
            self.marks_obtained = self.question.marks
        else:
            self.is_correct = False
            self.marks_obtained = 0
        super().save(*args, **kwargs)




