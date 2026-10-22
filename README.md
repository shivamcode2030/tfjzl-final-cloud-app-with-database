# Online Course App — Final Project

This Django project extends the IBM Skills Network Online Course application with an exam and assessment feature.

## Implemented features

- Question, Choice, and Submission models
- Django admin support for exam management
- Bootstrap course detail page with lessons and exam questions
- Exam submission and result evaluation views
- Exam submission and result URL routes
- Detailed exam result page with score and per-question results

## Run

    pip install -r requirements.txt
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver
