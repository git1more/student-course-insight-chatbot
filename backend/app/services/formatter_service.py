from app.models.feedback import FeedbackComment

class FormatterService:
    def format_response(self, evidence_comments: list[FeedbackComment], sample_size: int, confidence: str, term: str):
        positives, watch_outs, evidence = [], [], []
        for comment in evidence_comments:
            excerpt = comment.comment_text[:160]
            evidence.append({'comment_id': comment.id, 'excerpt': excerpt, 'sentiment': comment.sentiment})
            if comment.sentiment == 'positive':
                positives.append(excerpt)
            else:
                watch_outs.append(excerpt)

        if positives and watch_outs:
            quick_take = 'Students generally see the course as practical and worthwhile, but several comments mention workload or coordination concerns.'
        elif positives:
            quick_take = 'Students generally describe the course positively with strong practical value.'
        else:
            quick_take = 'Students raised several concerns and trade-offs in their comments.'

        return {
            'quick_take': quick_take,
            'positives': positives[:3] or ['Students highlighted practical learning value.'],
            'watch_outs': watch_outs[:3] or ['Some comments indicate workload or coordination challenges.'],
            'evidence': evidence[:6],
            'sample_size': sample_size,
            'timeframe': term,
            'confidence': confidence,
            'blocked_by_privacy': False,
            'message': None,
        }

    def format_privacy_blocked(self, sample_size: int, term: str):
        return {
            'quick_take': '',
            'positives': [],
            'watch_outs': [],
            'evidence': [],
            'sample_size': sample_size,
            'timeframe': term,
            'confidence': 'Low',
            'blocked_by_privacy': True,
            'message': 'Not enough evidence to provide a representative summary for this course and term.',
        }

formatter_service = FormatterService()
