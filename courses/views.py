from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.conf import settings
from .models import (
    Category, Course, Lesson, Enrollment, LessonProgress,
    Quiz, Question, Answer, QuizAttempt, QuizResponse,
    Assignment, Submission, Certificate, CourseReview,
    Discussion, Reply, Notification, Payment, PromoCode,
    Wishlist, Badge, UserBadge, UserXP, XPTransaction,
    DailyChallenge, UserChallenge, ChatMessage
)
from .forms import (
    CourseForm, LessonForm, QuizForm, QuestionForm,
    AssignmentForm, SubmissionForm, ReviewForm,
    DiscussionForm, ReplyForm
)

# Gemini AI import
try:
    from google import genai

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# ==========================================
# DASHBOARD (Student)
# ==========================================
@login_required
def dashboard(request):
    user = request.user
    enrollments = Enrollment.objects.filter(student=user).select_related('course')

    xp_profile, _ = UserXP.objects.get_or_create(user=user)
    recent_activities = XPTransaction.objects.filter(user=user).order_by('-created_at')[:5]
    certificates = Certificate.objects.filter(student=user).order_by('-issued_at')[:3]
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')[:6]

    enrolled_course_ids = enrollments.values_list('course_id', flat=True)
    recommended_courses = Course.objects.filter(
        is_published=True
    ).exclude(id__in=enrolled_course_ids).order_by('-created_at')[:4]

    completed_count = enrollments.filter(completed=True).count()
    in_progress_count = enrollments.filter(completed=False).count()

    context = {
        'enrollments': enrollments[:6],
        'xp_profile': xp_profile,
        'recent_activities': recent_activities,
        'certificates': certificates,
        'user_badges': user_badges,
        'recommended_courses': recommended_courses,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'total_courses': enrollments.count(),
    }
    return render(request, 'courses/dashboard.html', context)


# ==========================================
# COURSE LIST & DETAIL
# ==========================================
def course_list(request):
    courses = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    categories = Category.objects.filter(is_active=True).annotate(course_count=Count('courses'))

    query = request.GET.get('q')
    if query:
        courses = courses.filter(Q(title__icontains=query) | Q(description__icontains=query))

    category_slug = request.GET.get('category')
    if category_slug:
        courses = courses.filter(category__slug=category_slug)

    level = request.GET.get('level')
    if level:
        courses = courses.filter(level=level)

    is_free = request.GET.get('free')
    if is_free:
        courses = courses.filter(is_free=True)

    sort = request.GET.get('sort', '-created_at')
    if sort == 'popular':
        courses = courses.order_by('-total_students')
    elif sort == 'rating':
        courses = courses.order_by('-average_rating')
    elif sort == 'price_low':
        courses = courses.order_by('price')
    elif sort == 'price_high':
        courses = courses.order_by('-price')
    else:
        courses = courses.order_by('-created_at')

    paginator = Paginator(courses, 12)
    page = request.GET.get('page')
    courses = paginator.get_page(page)

    context = {
        'courses': courses,
        'categories': categories,
        'current_category': category_slug,
        'current_level': level,
        'current_sort': sort,
        'query': query,
    }
    return render(request, 'courses/course_list.html', context)


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    lessons = course.lessons.filter(is_published=True).order_by('order')
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')[:10]

    is_enrolled = False
    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        is_enrolled = enrollment is not None

    related_courses = Course.objects.filter(
        category=course.category, is_published=True
    ).exclude(id=course.id)[:4]

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, course=course).exists()

    context = {
        'course': course,
        'lessons': lessons,
        'reviews': reviews,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'related_courses': related_courses,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'courses/course_detail.html', context)


# ==========================================
# ENROLLMENT
# ==========================================
@login_required
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.info(request, "Siz allaqachon bu kursga yozilgansiz!")
        return redirect('course_learn', slug=slug)

    if course.is_free:
        Enrollment.objects.create(student=request.user, course=course)
        course.total_students += 1
        course.save()
        messages.success(request, f"'{course.title}' kursiga muvaffaqiyatli yozildingiz!")
        return redirect('course_learn', slug=slug)

    return redirect('payment_checkout', slug=slug)


@login_required
def my_courses(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related('course')

    status = request.GET.get('status')
    if status == 'completed':
        enrollments = enrollments.filter(completed=True)
    elif status == 'in_progress':
        enrollments = enrollments.filter(completed=False)

    context = {
        'enrollments': enrollments,
        'current_status': status,
    }
    return render(request, 'courses/my_courses.html', context)


# ==========================================
# LEARNING
# ==========================================
@login_required
def course_learn(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    lessons = course.lessons.filter(is_published=True).order_by('order')

    current_lesson_id = request.GET.get('lesson')
    if current_lesson_id:
        current_lesson = get_object_or_404(Lesson, id=current_lesson_id, course=course)
    else:
        completed_ids = LessonProgress.objects.filter(
            student=request.user, lesson__course=course, completed=True
        ).values_list('lesson_id', flat=True)
        current_lesson = lessons.exclude(id__in=completed_ids).first() or lessons.first()

    completed_lessons = LessonProgress.objects.filter(
        student=request.user, lesson__course=course, completed=True
    ).values_list('lesson_id', flat=True)

    context = {
        'course': course,
        'enrollment': enrollment,
        'lessons': lessons,
        'current_lesson': current_lesson,
        'completed_lessons': list(completed_lessons),
    }
    return render(request, 'courses/course_learn.html', context)


@login_required
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)

    progress, created = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)

    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(lesson.xp_reward, f"'{lesson.title}' darsini tugatish")

        total_lessons = lesson.course.lessons.filter(is_published=True).count()
        completed_lessons = LessonProgress.objects.filter(
            student=request.user, lesson__course=lesson.course, completed=True
        ).count()

        enrollment.progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

        if enrollment.progress >= 100:
            enrollment.completed = True
            enrollment.completed_at = timezone.now()
            Certificate.objects.get_or_create(student=request.user, course=lesson.course)
            messages.success(request, f"Tabriklaymiz! '{lesson.course.title}' kursini tugatdingiz!")

        enrollment.save()

    next_lesson = lesson.course.lessons.filter(is_published=True, order__gt=lesson.order).first()

    if next_lesson:
        return redirect(f"{request.path.rsplit('/', 2)[0]}/?lesson={next_lesson.id}")

    return redirect('course_learn', slug=lesson.course.slug)


# ==========================================
# QUIZ
# ==========================================
@login_required
def quiz_detail(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=quiz.lesson.course)

    attempts = QuizAttempt.objects.filter(student=request.user, quiz=quiz).order_by('-started_at')
    best_score = attempts.order_by('-score').first()
    can_attempt = attempts.count() < quiz.max_attempts

    context = {
        'quiz': quiz,
        'attempts': attempts,
        'best_score': best_score,
        'can_attempt': can_attempt,
    }
    return render(request, 'courses/quiz_detail.html', context)


@login_required
def quiz_take(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    attempts_count = QuizAttempt.objects.filter(student=request.user, quiz=quiz).count()
    if attempts_count >= quiz.max_attempts:
        messages.error(request, "Maksimal urinish soniga yetdingiz!")
        return redirect('quiz_detail', pk=pk)

    questions = quiz.questions.all()
    if quiz.shuffle_questions:
        questions = questions.order_by('?')

    if request.method == 'POST':
        attempt = QuizAttempt.objects.create(student=request.user, quiz=quiz)

        correct = 0
        total_points = 0
        earned_points = 0

        for question in questions:
            total_points += question.points
            selected_ids = request.POST.getlist(f'question_{question.id}')

            QuizResponse.objects.create(
                attempt=attempt,
                question=question,
                selected_answers=','.join(selected_ids)
            )

            correct_ids = set(str(a.id) for a in question.answers.filter(is_correct=True))
            if correct_ids == set(selected_ids):
                correct += 1
                earned_points += question.points

        score = int((earned_points / total_points) * 100) if total_points > 0 else 0
        passed = score >= quiz.passing_score

        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.correct_answers = correct
        attempt.wrong_answers = len(questions) - correct

        if passed:
            attempt.xp_earned = quiz.xp_reward
            xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
            xp_profile.add_xp(quiz.xp_reward, f"'{quiz.title}' testini topshirish")

        attempt.save()
        return redirect('quiz_result', pk=attempt.pk)

    return render(request, 'courses/quiz_take.html', {'quiz': quiz, 'questions': questions})


@login_required
def quiz_result(request, pk):
    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)
    responses = attempt.responses.select_related('question')
    return render(request, 'courses/quiz_result.html', {'attempt': attempt, 'responses': responses})


@login_required
def quiz_statistics(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    if quiz.lesson.course.teacher != request.user:
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('dashboard')

    attempts = QuizAttempt.objects.filter(quiz=quiz)
    total_attempts = attempts.count()
    passed_attempts = attempts.filter(passed=True).count()
    avg_score = attempts.aggregate(avg=Avg('score'))['avg'] or 0
    pass_rate = (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0

    context = {
        'quiz': quiz,
        'total_attempts': total_attempts,
        'passed_attempts': passed_attempts,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
        'attempts': attempts.order_by('-started_at')[:20],
    }
    return render(request, 'courses/quiz_statistics.html', context)


# ==========================================
# ASSIGNMENT
# ==========================================
@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    submission = Submission.objects.filter(student=request.user, assignment=assignment).first()
    return render(request, 'courses/assignment_detail.html', {'assignment': assignment, 'submission': submission})


@login_required
def assignment_submit(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)

    existing = Submission.objects.filter(student=request.user, assignment=assignment).first()
    if existing:
        messages.info(request, "Siz allaqachon topshiriq yuborgansiz!")
        return redirect('assignment_detail', pk=pk)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = request.user
            submission.assignment = assignment
            submission.save()
            messages.success(request, "Topshiriq yuborildi!")
            return redirect('assignment_detail', pk=pk)
    else:
        form = SubmissionForm()

    return render(request, 'courses/assignment_submit.html', {'form': form, 'assignment': assignment})


# ==========================================
# CERTIFICATE
# ==========================================
@login_required
def my_certificates(request):
    certificates = Certificate.objects.filter(student=request.user).select_related('course')
    return render(request, 'courses/my_certificates.html', {'certificates': certificates})


@login_required
def certificate_detail(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk, student=request.user)
    return render(request, 'courses/certificate_detail.html', {'certificate': certificate})


def certificate_verify(request, certificate_number):
    certificate = get_object_or_404(Certificate, certificate_number=certificate_number)
    return render(request, 'courses/certificate_verify.html', {'certificate': certificate})


# ==========================================
# REVIEW
# ==========================================
@login_required
def review_create(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.error(request, "Sharh qoldirish uchun kursga yozilishingiz kerak!")
        return redirect('course_detail', slug=slug)

    if CourseReview.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "Siz allaqachon sharh qoldirgansiz!")
        return redirect('course_detail', slug=slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.course = course
            review.save()

            avg_rating = course.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            course.average_rating = avg_rating
            course.total_reviews = course.reviews.count()
            course.save()

            messages.success(request, "Sharh qo'shildi!")
            return redirect('course_detail', slug=slug)
    else:
        form = ReviewForm()

    return render(request, 'courses/review_form.html', {'form': form, 'course': course})


@login_required
def review_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')
    paginator = Paginator(reviews, 10)
    reviews = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/review_list.html', {'course': course, 'reviews': reviews})


# ==========================================
# DISCUSSION
# ==========================================
@login_required
def discussion_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    discussions = course.discussions.order_by('-is_pinned', '-created_at')
    return render(request, 'courses/discussion_list.html', {'course': course, 'discussions': discussions})


@login_required
def discussion_create(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.course = course
            discussion.author = request.user
            discussion.save()
            messages.success(request, "Muhokama yaratildi!")
            return redirect('discussion_list', slug=slug)
    else:
        form = DiscussionForm()

    return render(request, 'courses/discussion_form.html', {'form': form, 'course': course})


@login_required
def discussion_detail(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk)
    discussion.views_count += 1
    discussion.save()

    replies = discussion.replies.order_by('created_at')

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.discussion = discussion
            reply.author = request.user
            reply.save()
            messages.success(request, "Javob qo'shildi!")
            return redirect('discussion_detail', pk=pk)
    else:
        form = ReplyForm()

    return render(request, 'courses/discussion_detail.html',
                  {'discussion': discussion, 'replies': replies, 'form': form})


@login_required
def reply_delete(request, pk):
    reply = get_object_or_404(Reply, pk=pk, author=request.user)
    discussion_pk = reply.discussion.pk
    if request.method == 'POST':
        reply.delete()
        messages.success(request, "Javob o'chirildi!")
    return redirect('discussion_detail', pk=discussion_pk)


# ==========================================
# NOTIFICATION
# ==========================================
@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
        return redirect('notification_list')

    paginator = Paginator(notifications, 20)
    notifications = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/notification_list.html', {'notifications': notifications})


@login_required
def notification_recent(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message[:50],
        'type': n.notification_type,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
    } for n in notifications]

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})


# ==========================================
# PAYMENT
# ==========================================
@login_required
def payment_checkout(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_learn', slug=slug)

    final_price = course.discount_price if course.discount_price else course.price
    discount = 0
    promo_code = None

    if request.method == 'POST':
        code = request.POST.get('promo_code', '').strip().upper()
        if code:
            try:
                promo = PromoCode.objects.get(
                    code=code, is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now()
                )
                if promo.current_uses < promo.max_uses:
                    if promo.discount_type == 'percent':
                        discount = final_price * (promo.discount_value / 100)
                    else:
                        discount = promo.discount_value
                    final_price = max(0, final_price - discount)
                    promo_code = promo
                    messages.success(request, f"Promo kod qo'llanildi!")
            except PromoCode.DoesNotExist:
                messages.error(request, "Noto'g'ri promo kod!")

    return render(request, 'courses/payment_checkout.html', {
        'course': course, 'final_price': final_price, 'discount': discount, 'promo_code': promo_code
    })


@login_required
def payment_process(request, slug):
    if request.method != 'POST':
        return redirect('payment_checkout', slug=slug)

    course = get_object_or_404(Course, slug=slug)
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method', 'payme')

    Payment.objects.create(
        student=request.user, course=course, amount=amount,
        payment_method=payment_method, status='completed',
        transaction_id=f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    )

    Enrollment.objects.create(student=request.user, course=course)
    course.total_students += 1
    course.save()

    return redirect('payment_success', slug=slug)


@login_required
def payment_success(request, slug):
    course = get_object_or_404(Course, slug=slug)
    return render(request, 'courses/payment_success.html', {'course': course})


# ==========================================
# WISHLIST
# ==========================================
@login_required
def wishlist_view(request):
    wishlist = Wishlist.objects.filter(user=request.user).select_related('course')
    return render(request, 'courses/wishlist.html', {'wishlist': wishlist})


@login_required
def wishlist_toggle(request, slug):
    course = get_object_or_404(Course, slug=slug)
    wishlist_item = Wishlist.objects.filter(user=request.user, course=course)

    if wishlist_item.exists():
        wishlist_item.delete()
        messages.info(request, "Kurs istaklar ro'yxatidan o'chirildi")
    else:
        Wishlist.objects.create(user=request.user, course=course)
        messages.success(request, "Kurs istaklar ro'yxatiga qo'shildi")

    return redirect(request.META.get('HTTP_REFERER', 'course_list'))


# ==========================================
# TEACHER PANEL
# ==========================================
@login_required
def teacher_dashboard(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
        messages.error(request, "Sizda o'qituvchi huquqi yo'q!")
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user)
    total_students = Enrollment.objects.filter(course__teacher=request.user).count()
    total_revenue = Payment.objects.filter(
        course__teacher=request.user, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    recent_enrollments = Enrollment.objects.filter(
        course__teacher=request.user
    ).select_related('student', 'course').order_by('-enrolled_at')[:10]

    context = {
        'courses': courses,
        'total_students': total_students,
        'total_courses': courses.count(),
        'total_revenue': total_revenue,
        'recent_enrollments': recent_enrollments,
    }
    return render(request, 'courses/teacher/dashboard.html', context)


@login_required
def teacher_courses(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
        messages.error(request, "Sizda o'qituvchi huquqi yo'q!")
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user).order_by('-created_at')
    for course in courses:
        course.enrolled_count = Enrollment.objects.filter(course=course).count()

    return render(request, 'courses/teacher/courses.html', {'courses': courses})


@login_required
def teacher_course_create(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
        messages.error(request, "Sizda o'qituvchi huquqi yo'q!")
        return redirect('dashboard')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, "Kurs muvaffaqiyatli yaratildi!")
            return redirect('teacher_course_edit', slug=course.slug)
    else:
        form = CourseForm()

    return render(request, 'courses/teacher/course_create.html', {'form': form})


@login_required
def teacher_course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Kurs yangilandi!")
            return redirect('teacher_courses')
    else:
        form = CourseForm(instance=course)

    lessons = course.lessons.all().order_by('order')
    return render(request, 'courses/teacher/course_edit.html', {'form': form, 'course': course, 'lessons': lessons})


@login_required
def teacher_course_students(request, slug):
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student').order_by('-enrolled_at')

    status = request.GET.get('status')
    if status == 'completed':
        enrollments = enrollments.filter(completed=True)
    elif status == 'in_progress':
        enrollments = enrollments.filter(completed=False)

    context = {
        'course': course,
        'enrollments': enrollments,
        'current_status': status,
        'total_count': Enrollment.objects.filter(course=course).count(),
        'completed_count': Enrollment.objects.filter(course=course, completed=True).count(),
    }
    return render(request, 'courses/teacher/course_students.html', context)


@login_required
def teacher_course_delete(request, slug):
    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == 'POST':
        course.delete()
        messages.success(request, "Kurs o'chirildi!")
        return redirect('teacher_courses')

    return render(request, 'courses/teacher/course_delete.html', {'course': course})


@login_required
def teacher_lesson_create(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, teacher=request.user)

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            last_order = course.lessons.order_by('-order').first()
            lesson.order = (last_order.order + 1) if last_order else 1
            lesson.save()
            messages.success(request, "Dars qo'shildi!")
            return redirect('teacher_course_edit', slug=course.slug)
    else:
        form = LessonForm()

    return render(request, 'courses/teacher/lesson_form.html', {'form': form, 'course': course, 'action': 'create'})


@login_required
def teacher_lesson_edit(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, course__teacher=request.user)

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, "Dars yangilandi!")
            return redirect('teacher_course_edit', slug=lesson.course.slug)
    else:
        form = LessonForm(instance=lesson)

    return render(request, 'courses/teacher/lesson_form.html',
                  {'form': form, 'lesson': lesson, 'course': lesson.course, 'action': 'edit'})


@login_required
def teacher_lesson_delete(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, course__teacher=request.user)
    course_slug = lesson.course.slug

    if request.method == 'POST':
        lesson.delete()
        messages.success(request, "Dars o'chirildi!")
        return redirect('teacher_course_edit', slug=course_slug)

    return render(request, 'courses/teacher/lesson_delete.html', {'lesson': lesson})


@login_required
def teacher_statistics(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_teacher:
        messages.error(request, "Sizda o'qituvchi huquqi yo'q!")
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user)
    total_students = Enrollment.objects.filter(course__teacher=request.user).count()
    completed_students = Enrollment.objects.filter(course__teacher=request.user, completed=True).count()
    total_revenue = Payment.objects.filter(
        course__teacher=request.user, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'courses': courses,
        'total_courses': courses.count(),
        'total_students': total_students,
        'completed_students': completed_students,
        'total_revenue': total_revenue,
    }
    return render(request, 'courses/teacher/statistics.html', context)


# ==========================================
# GAMIFICATION
# ==========================================
@login_required
def gamification_profile(request):
    xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
    user_badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    transactions = XPTransaction.objects.filter(user=request.user).order_by('-created_at')[:20]

    return render(request, 'courses/gamification/profile.html', {
        'xp_profile': xp_profile, 'user_badges': user_badges, 'transactions': transactions
    })


@login_required
def leaderboard(request):
    top_users = UserXP.objects.select_related('user').order_by('-total_xp')[:50]
    user_xp, _ = UserXP.objects.get_or_create(user=request.user)
    user_rank = UserXP.objects.filter(total_xp__gt=user_xp.total_xp).count() + 1

    return render(request, 'courses/gamification/leaderboard.html', {
        'top_users': top_users, 'user_rank': user_rank, 'user_xp': user_xp
    })


@login_required
def daily_challenges(request):
    today = timezone.now().date()
    challenges = DailyChallenge.objects.filter(date=today, is_active=True)
    completed_ids = UserChallenge.objects.filter(
        user=request.user, challenge__date=today
    ).values_list('challenge_id', flat=True)

    return render(request, 'courses/gamification/daily_challenges.html', {
        'challenges': challenges, 'completed_ids': list(completed_ids)
    })


# ==========================================
# CHATBOT
# ==========================================
def generate_ai_response(message, course=None):
    if not GEMINI_AVAILABLE:
        return "AI xizmati hozircha mavjud emas."

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        system_prompt = """Sen LMS platformasining AI yordamchisisisan. O'zbek tilida javob ber.
Dasturlash, Django, Python va boshqa mavzularda yordam ber. Qisqa va foydali javoblar ber."""

        if course:
            system_prompt += f"\n\nHozir talaba '{course.title}' kursini o'qiyapti."

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"{system_prompt}\n\nSavol: {message}"
        )
        return response.text

    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg:
            return "⚠️ API limit tugagan. 1 daqiqa kutib qayta urinib ko'ring."
        return f"Xatolik: {error_msg[:100]}"


@login_required
def chatbot_view(request, slug=None):
    course = get_object_or_404(Course, slug=slug) if slug else None
    messages_list = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:20]
    return render(request, 'courses/chatbot/chat.html', {'course': course, 'messages': reversed(list(messages_list))})


@login_required
def chatbot_send(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        course_slug = request.POST.get('course_slug')

        if not message:
            return JsonResponse({'error': 'Xabar bo\'sh'}, status=400)

        course = get_object_or_404(Course, slug=course_slug) if course_slug else None
        ai_response = generate_ai_response(message, course)

        chat_message = ChatMessage.objects.create(
            user=request.user, course=course, message=message, response=ai_response
        )

        return JsonResponse({
            'success': True, 'message': message, 'response': ai_response,
            'created_at': chat_message.created_at.strftime('%H:%M')
        })

    return JsonResponse({'error': 'POST kerak'}, status=405)


@login_required
def chatbot_history(request):
    messages_list = ChatMessage.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(messages_list, 20)
    return render(request, 'courses/chatbot/history.html', {'messages': paginator.get_page(request.GET.get('page'))})


@login_required
def chatbot_clear(request):
    ChatMessage.objects.filter(user=request.user).delete()
    messages.success(request, "Barcha xabarlar o'chirildi!")
    return redirect('chatbot_view')


# ==========================================
# CODE EDITOR
# ==========================================
@login_required
def code_editor(request):
    return render(request, 'courses/code_editor/editor.html')


# ==========================================
# STUDENT STATISTICS
# ==========================================
@login_required
def student_statistics(request):
    enrollments = Enrollment.objects.filter(student=request.user)
    return render(request, 'courses/student_statistics.html', {
        'total_enrolled': enrollments.count(),
        'completed': enrollments.filter(completed=True).count(),
        'in_progress': enrollments.filter(completed=False).count(),
    })


# ==========================================
# HOME
# ==========================================
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    featured_courses = Course.objects.filter(is_published=True, is_featured=True)[:6]
    categories = Category.objects.filter(is_active=True)[:8]
    return render(request, 'home.html', {'featured_courses': featured_courses, 'categories': categories})


# ==========================================
# CODE EDITOR & EXECUTION
# ==========================================
@login_required
def code_editor(request):
    return render(request, 'courses/code_editor/editor.html')


@login_required
def code_execute(request):
    """Python kodini xavfsiz ishga tushirish"""
    import subprocess
    import tempfile
    import os

    if request.method != 'POST':
        return JsonResponse({'error': 'POST kerak'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', 'python')

        if not code.strip():
            return JsonResponse({'error': 'Kod bo\'sh'}, status=400)

        if language == 'python':
            # Xavfsizlik: ba'zi funksiyalarni cheklash
            forbidden = ['import os', 'import subprocess', 'import sys', '__import__',
                         'eval(', 'exec(', 'open(', 'file(', 'input(']

            for f in forbidden:
                if f in code:
                    return JsonResponse({
                        'success': False,
                        'error': f"Xavfsizlik: '{f}' ishlatish taqiqlangan!"
                    })

            # Vaqtinchalik fayl yaratish
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name

            try:
                # Python ni ishga tushirish (timeout: 5 sekund)
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='utf-8'
                )

                if result.returncode == 0:
                    output = result.stdout if result.stdout else "Dastur muvaffaqiyatli ishga tushdi (natija yo'q)"
                    return JsonResponse({'success': True, 'output': output})
                else:
                    return JsonResponse({'success': False, 'error': result.stderr})

            finally:
                # Vaqtinchalik faylni o'chirish
                os.unlink(temp_file)

        return JsonResponse({'error': 'Noma\'lum til'}, status=400)

    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False,
            'error': 'Vaqt tugadi! Dastur 5 sekunddan ko\'p ishladi.'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Noto\'g\'ri JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})