from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    # Auth - Token olish
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Categories
    path('categories/', api_views.CategoryListView.as_view(), name='api_categories'),

    # Courses
    path('courses/', api_views.CourseListView.as_view(), name='api_courses'),
    path('courses/<slug:slug>/', api_views.CourseDetailView.as_view(), name='api_course_detail'),
    path('courses/<slug:slug>/enroll/', api_views.CourseEnrollView.as_view(), name='api_course_enroll'),
    path('courses/<slug:slug>/reviews/', api_views.CourseReviewsView.as_view(), name='api_course_reviews'),
    path('courses/<slug:slug>/reviews/create/', api_views.ReviewCreateView.as_view(), name='api_review_create'),

    # Enrollments
    path('my-courses/', api_views.MyEnrollmentsView.as_view(), name='api_my_courses'),

    # Lessons
    path('lessons/<int:pk>/', api_views.LessonDetailView.as_view(), name='api_lesson_detail'),
    path('lessons/<int:pk>/complete/', api_views.LessonCompleteView.as_view(), name='api_lesson_complete'),

    # Quizzes
    path('quizzes/<int:pk>/', api_views.QuizDetailView.as_view(), name='api_quiz_detail'),
    path('quizzes/<int:pk>/start/', api_views.QuizStartView.as_view(), name='api_quiz_start'),
    path('quizzes/attempt/<int:attempt_id>/submit/', api_views.QuizSubmitView.as_view(), name='api_quiz_submit'),
    path('my-quiz-attempts/', api_views.MyQuizAttemptsView.as_view(), name='api_my_quiz_attempts'),

    # Certificates
    path('my-certificates/', api_views.MyCertificatesView.as_view(), name='api_my_certificates'),
    path('certificates/<uuid:id>/verify/', api_views.CertificateVerifyView.as_view(), name='api_certificate_verify'),

    # User Profile
    path('profile/', api_views.UserProfileView.as_view(), name='api_profile'),
    path('stats/', api_views.UserStatsView.as_view(), name='api_stats'),

    # Leaderboard
    path('leaderboard/', api_views.LeaderboardView.as_view(), name='api_leaderboard'),

    # Search
    path('search/', api_views.SearchView.as_view(), name='api_search'),
]