from django.core.management.base import BaseCommand
from courses.models import Badge


class Command(BaseCommand):
    help = 'Standart badgelarni yaratish'

    def handle(self, *args, **options):
        badges = [
            # Kurs badgelari
            {'name': 'Birinchi qadam', 'slug': 'first-course', 'description': 'Birinchi kursni tugatdingiz!',
             'icon': 'bi-flag', 'color': '#10b981', 'badge_type': 'course', 'level': 'bronze', 'xp_reward': 100},
            {'name': '5 ta kurs', 'slug': 'five-courses', 'description': '5 ta kursni tugatdingiz!', 'icon': 'bi-book',
             'color': '#3b82f6', 'badge_type': 'course', 'level': 'silver', 'xp_reward': 250},
            {'name': '10 ta kurs', 'slug': 'ten-courses', 'description': '10 ta kursni tugatdingiz!',
             'icon': 'bi-books', 'color': '#8b5cf6', 'badge_type': 'course', 'level': 'gold', 'xp_reward': 500},
            {'name': 'Kurs ustasi', 'slug': 'course-master', 'description': '25 ta kursni tugatdingiz!',
             'icon': 'bi-mortarboard', 'color': '#f59e0b', 'badge_type': 'course', 'level': 'platinum',
             'xp_reward': 1000},

            # Quiz badgelari
            {'name': 'Birinchi quiz', 'slug': 'first-quiz', 'description': 'Birinchi quizdan o\'tdingiz!',
             'icon': 'bi-patch-check', 'color': '#10b981', 'badge_type': 'quiz', 'level': 'bronze', 'xp_reward': 50},
            {'name': 'Quiz Pro', 'slug': 'quiz-pro', 'description': '10 ta quizdan o\'tdingiz!',
             'icon': 'bi-check-circle', 'color': '#3b82f6', 'badge_type': 'quiz', 'level': 'silver', 'xp_reward': 200},
            {'name': 'Quiz Master', 'slug': 'quiz-master', 'description': '50 ta quizdan o\'tdingiz!',
             'icon': 'bi-trophy', 'color': '#f59e0b', 'badge_type': 'quiz', 'level': 'gold', 'xp_reward': 500},

            # Streak badgelari
            {'name': 'Haftalik streak', 'slug': 'week-streak', 'description': '7 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#ef4444', 'badge_type': 'streak', 'level': 'bronze', 'xp_reward': 100},
            {'name': 'Oylik streak', 'slug': 'month-streak', 'description': '30 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#f97316', 'badge_type': 'streak', 'level': 'gold', 'xp_reward': 500},
            {'name': '100 kunlik streak', 'slug': 'hundred-streak', 'description': '100 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#dc2626', 'badge_type': 'streak', 'level': 'diamond', 'xp_reward': 2000},

            # Daraja badgelari
            {'name': 'Daraja 5', 'slug': 'level-5', 'description': '5-darajaga yetdingiz!', 'icon': 'bi-star',
             'color': '#6366f1', 'badge_type': 'special', 'level': 'bronze', 'xp_reward': 100},
            {'name': 'Daraja 10', 'slug': 'level-10', 'description': '10-darajaga yetdingiz!', 'icon': 'bi-star-fill',
             'color': '#8b5cf6', 'badge_type': 'special', 'level': 'silver', 'xp_reward': 300},
            {'name': 'Daraja 25', 'slug': 'level-25', 'description': '25-darajaga yetdingiz!', 'icon': 'bi-stars',
             'color': '#f59e0b', 'badge_type': 'special', 'level': 'gold', 'xp_reward': 1000},

            # Ijtimoiy badgelar
            {'name': 'Yordamchi', 'slug': 'helper', 'description': 'Forumda 10 ta yechim belgilandi!',
             'icon': 'bi-hand-thumbs-up', 'color': '#10b981', 'badge_type': 'social', 'level': 'silver',
             'xp_reward': 200},
            {'name': 'Faol ishtirokchi', 'slug': 'active-member', 'description': 'Forumda 50 ta javob yozdingiz!',
             'icon': 'bi-chat-dots', 'color': '#3b82f6', 'badge_type': 'social', 'level': 'gold', 'xp_reward': 300},
        ]

        created = 0
        for badge_data in badges:
            badge, is_created = Badge.objects.get_or_create(
                slug=badge_data['slug'],
                defaults=badge_data
            )
            if is_created:
                created += 1
                self.stdout.write(f"  ✓ {badge.name} yaratildi")

        self.stdout.write(self.style.SUCCESS(f'\n{created} ta badge yaratildi!'))