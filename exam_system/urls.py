from django.contrib import admin
from django.urls import path
from accounts import views as av
from exams import views as ev

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', av.login_view, name='home'),
    path('login/', av.login_view, name='login'),
    path('register/', av.register_view, name='register'),
    path('logout/', av.logout_view, name='logout'),
    path('dashboard/', av.dashboard, name='dashboard'),
    path('profile/', av.profile_view, name='profile'),
    # Admin
    path('admin-dashboard/', ev.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', ev.manage_users, name='manage_users'),
    path('toggle-user/<int:user_id>/', ev.toggle_user, name='toggle_user'),
    path('all-results/', ev.all_results, name='all_results'),
    # Teacher
    path('teacher-dashboard/', ev.teacher_dashboard, name='teacher_dashboard'),
    path('create-subject/', ev.create_subject, name='create_subject'),
    path('create-question/', ev.create_question, name='create_question'),
    path('question-bank/', ev.question_bank, name='question_bank'),
    path('delete-question/<int:q_id>/', ev.delete_question, name='delete_question'),
    path('create-exam/', ev.create_exam, name='create_exam'),
    path('exam-results/<int:exam_id>/', ev.exam_results, name='exam_results'),
    # Student
    path('student-dashboard/', ev.student_dashboard, name='student_dashboard'),
    path('start-exam/<int:exam_id>/', ev.start_exam, name='start_exam'),
    path('submit-exam/<int:exam_id>/', ev.submit_exam, name='submit_exam'),
    path('result/<int:attempt_id>/', ev.exam_result_detail, name='exam_result_detail'),
    path('my-results/', ev.my_results, name='my_results'),
]
