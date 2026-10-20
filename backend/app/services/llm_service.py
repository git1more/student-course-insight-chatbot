import json
from openai import OpenAI
from app.core.config import settings
from app.db.models import FeedbackComment

# IMPORTANT: The dataset is entirely "Needs Improvement" feedback from students.
# There are NO explicit positive comments.

_SYSTEM_PROMPT = """\
You are an academic course insight analyst for an Australian university. \
You analyse anonymised student feedback from the "Needs Improvement" section of course surveys. \
ALL comments in the dataset describe areas students want improved — there are no explicit praise comments. \
Produce structured, evidence-grounded academic reports for course coordinators and teaching staff.

Key rules:
- Base every claim strictly on the provided evidence. Never fabricate quotes or invent data.
- "ranked_themes": rank issues by how frequently they appear across the evidence (volume) and whether \
  they appear in recent years (recency). Volume = High if mentioned in 3+ excerpts, Medium if 2, Low if 1.
- "interpretation": identify the underlying drivers behind the top themes and note any counter-signals \
  or conflicting views in the evidence.
- "recommended_actions": practical, specific actions. owner = who should act \
  (e.g. "Course Coordinator", "Teaching Team", "Faculty"). \
  effort = Low/Medium/High. impact = Low/Medium/High.
- Always respond with valid JSON matching the schema — no markdown fences."""

_USER_TEMPLATE = """\
Analyse {n} "Needs Improvement" student feedback comments for **{program}** (year: {year}).

User question: "{question}"

Top {count} most semantically relevant comment excerpts:
{evidence_block}

Respond ONLY with this exact JSON — no extra keys, no markdown:
{{
  "executive_summary": "<factual summary ≤120 words directly answering the question, noting this is improvement-focused feedback and citing the sample size>",
  "ranked_themes": [
    {{"theme": "<concise label>", "volume": "High|Medium|Low", "recency": "Recent|Stable|Declining"}},
    {{"theme": "<concise label>", "volume": "High|Medium|Low", "recency": "Recent|Stable|Declining"}},
    {{"theme": "<concise label>", "volume": "High|Medium|Low", "recency": "Recent|Stable|Declining"}}
  ],
  "interpretation": "<2-3 sentences on the underlying drivers of the top themes and any counter-signals or conflicting views in the evidence>",
  "recommended_actions": [
    {{"action": "<specific action>", "owner": "<who>", "effort": "Low|Medium|High", "impact": "Low|Medium|High"}},
    {{"action": "<specific action>", "owner": "<who>", "effort": "Low|Medium|High", "impact": "Low|Medium|High"}},
    {{"action": "<specific action>", "owner": "<who>", "effort": "Low|Medium|High", "impact": "Low|Medium|High"}}
  ],
  "limitations": "<one sentence on data limitations, e.g. only improvement feedback, single program, year range>",
  "contradiction_detected": <true if evidence shows conflicting views on the same issue, else false>,
  "follow_up_questions": [
    "<follow-up question 1>",
    "<follow-up question 2>",
    "<follow-up question 3>"
  ]
}}

Rules:
- executive_summary: ≤120 words.
- ranked_themes: 3–5 items, ordered from highest to lowest volume.
- recommended_actions: 3 items minimum.
- follow_up_questions: exactly 3.
"""


class LLMService:
    def __init__(self):
        self._client = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.llm_api_key or settings.openai_api_key,
                base_url=settings.llm_base_url or None,
            )
        return self._client

    def generate_structured_response(
        self,
        program: str,
        year: str | None,
        question: str,
        comments: list[FeedbackComment],
        sample_size: int,
    ) -> dict:
        evidence_lines = [
            f'[#{c.comment_id}]: "{c.comment_text[:280]}"'
            for c in comments
        ]
        evidence_block = '\n'.join(evidence_lines)

        user_msg = _USER_TEMPLATE.format(
            n=sample_size,
            program=program,
            year=year or 'all years',
            question=question,
            count=len(comments),
            evidence_block=evidence_block,
        )

        response = self.client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {'role': 'system', 'content': _SYSTEM_PROMPT},
                {'role': 'user', 'content': user_msg},
            ],
            response_format={'type': 'json_object'},
            temperature=0.3,
        )

        raw = response.choices[0].message.content
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = _fallback_response()

        return _validate_and_fix(data)


def _fallback_response() -> dict:
    return {
        'executive_summary': 'Unable to generate a structured response. Please try again.',
        'ranked_themes': [
            {'theme': 'Unable to analyse themes', 'volume': 'Low', 'recency': 'Stable'},
        ],
        'interpretation': 'Analysis could not be completed. Please retry.',
        'recommended_actions': [
            {'action': 'Review the course outline', 'owner': 'Course Coordinator', 'effort': 'Low', 'impact': 'Medium'},
        ],
        'limitations': 'Response generation failed — results may be incomplete.',
        'contradiction_detected': False,
        'follow_up_questions': [
            'What aspects of teaching quality do students mention most?',
            'How does the workload compare across years?',
            'What practical tips do students offer for success in this program?',
        ],
    }


def _validate_and_fix(data: dict) -> dict:
    data.setdefault('executive_summary', 'Summary not available.')
    data.setdefault('ranked_themes', [{'theme': 'No themes identified', 'volume': 'Low', 'recency': 'Stable'}])
    data.setdefault('interpretation', 'No interpretation available.')
    data.setdefault('recommended_actions', [
        {'action': 'Consult the course handbook', 'owner': 'Course Coordinator', 'effort': 'Low', 'impact': 'Low'},
    ])
    data.setdefault('limitations', 'Based on improvement-focused feedback only.')
    data.setdefault('contradiction_detected', False)
    data.setdefault('follow_up_questions', [
        'What are the main teaching quality concerns?',
        'How does workload affect student experience?',
        'What practical tips do students share?',
    ])

    data['ranked_themes'] = data['ranked_themes'][:5]
    data['recommended_actions'] = data['recommended_actions'][:5]
    data['follow_up_questions'] = (data['follow_up_questions'] + ['What else would you like to explore?'])[:3]

    for t in data['ranked_themes']:
        t.setdefault('volume', 'Low')
        t.setdefault('recency', 'Stable')

    for a in data['recommended_actions']:
        a.setdefault('owner', 'Course Coordinator')
        a.setdefault('effort', 'Medium')
        a.setdefault('impact', 'Medium')

    return data


llm_service = LLMService()
