from assessment_core.models import Attempt
from decimal import Decimal


class AutoGrader:
    def grade_attempt(self, attempt_id):
        attempt = Attempt.objects.get(id=attempt_id)
        total_score = Decimal('0.00')
        max_score = Decimal('0.00')

        for response in attempt.responses.all():
            question = response.question
            max_score += question.points

            if question.question_type == 'MCQ':
                selected = response.response_data.get('selected')
                for option in question.options or []:
                    if option.get('text') == selected and option.get('correct'):
                        points = question.points
                        break
                else:
                    points = Decimal('0.00')
            else:
                points = Decimal('0.00')

            response.points_awarded = points
            response.save()
            total_score += points

        attempt.raw_score = total_score
        attempt.max_score = max_score
        attempt.percentage = (total_score / max_score * 100) if max_score > 0 else 0
        attempt.status = 'GRADED'
        attempt.save()

        return {
            'score': float(total_score),
            'max_score': float(max_score),
            'percentage': float(attempt.percentage)
        }
