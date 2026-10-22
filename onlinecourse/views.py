from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

from .models import (
    Choice,
    Course,
    Enrollment,
    Question,
    Submission,
)


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context,
        )

    username = request.POST['username']
    password = request.POST['psw']
    first_name = request.POST['firstname']
    last_name = request.POST['lastname']

    if User.objects.filter(username=username).exists():
        context['message'] = "User already exists."
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context,
        )

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
    )
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = "Invalid username or password."
        return render(
            request,
            'onlinecourse/user_login_bootstrap.html',
            context,
        )
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    if user.id is not None:
        return Enrollment.objects.filter(user=user, course=course).exists()
    return False


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if not user.is_authenticated:
        return redirect('onlinecourse:login')

    if not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse(viewname='onlinecourse:course_details', args=(course.id,))
    )


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice_'):
            try:
                submitted_answers.append(int(request.POST[key]))
            except (TypeError, ValueError):
                continue
    return submitted_answers


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not request.user.is_authenticated:
        return redirect('onlinecourse:login')

    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course,
    )

    submission = Submission.objects.create(enrollment=enrollment)

    selected_ids = extract_answers(request)
    choices = Choice.objects.filter(
        id__in=selected_ids,
        question__course=course,
    )
    submission.choices.set(choices)

    return redirect(
        'onlinecourse:show_exam_result',
        course_id=course.id,
        submission_id=submission.id,
    )


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course,
    )

    selected_choices = list(submission.choices.select_related('question'))
    selected_ids = {choice.id for choice in selected_choices}

    questions = list(
        Question.objects.filter(course=course)
        .prefetch_related('choice_set')
        .order_by('id')
    )

    total_points = sum(question.grade for question in questions)
    earned_points = 0
    results = []

    for question in questions:
        selected = [
            choice for choice in selected_choices
            if choice.question_id == question.id
        ]
        selected_correct = [
            choice for choice in selected
            if choice.is_correct
        ]
        all_correct = (
            bool(selected)
            and len(selected) == question.choice_set.filter(
                is_correct=True
            ).count()
            and len(selected_correct) == len(selected)
        )

        if all_correct:
            earned_points += question.grade

        correct_choices = list(question.choice_set.filter(is_correct=True))
        results.append({
            'question': question,
            'selected': selected,
            'selected_ids': selected_ids,
            'correct_choices': correct_choices,
            'is_correct': all_correct,
        })

    grade = (
        round((earned_points / total_points) * 100, 2)
        if total_points
        else 0
    )

    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        {
            'course': course,
            'submission': submission,
            'grade': grade,
            'earned_points': earned_points,
            'total_points': total_points,
            'results': results,
        },
    )
