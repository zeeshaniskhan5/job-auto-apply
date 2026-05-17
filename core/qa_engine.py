import re
import logging

logger = logging.getLogger(__name__)


class QAEngine:
    """Keyword-based screening question answerer."""

    def __init__(self, config: dict):
        self.personal = config.get("personal", {})
        self.saved = config.get("answers", {})

    def answer(self, question: str) -> str:
        q = question.lower().strip()

        # Try saved answers first (keyword match)
        for keyword, ans in self.saved.items():
            if keyword.lower() in q:
                return str(ans)

        # Built-in fallbacks
        if any(w in q for w in ["experience", "years"]):
            return str(self.personal.get("years_of_experience", "3"))
        if any(w in q for w in ["salary", "ctc", "package", "compensation"]):
            return str(self.personal.get("expected_salary", "As per company norms"))
        if any(w in q for w in ["notice", "joining", "available"]):
            return str(self.personal.get("notice_period", "30 days"))
        if any(w in q for w in ["phone", "mobile", "contact"]):
            return str(self.personal.get("phone", ""))
        if any(w in q for w in ["city", "location", "relocat"]):
            return str(self.personal.get("location", "Open to relocation"))
        if any(w in q for w in ["currently", "current company", "employer"]):
            return str(self.personal.get("current_company", "Currently looking"))
        if any(w in q for w in ["linkedin", "profile url"]):
            return str(self.personal.get("linkedin_url", ""))
        if any(w in q for w in ["website", "portfolio", "github"]):
            return str(self.personal.get("portfolio_url", ""))
        if any(w in q for w in ["gender"]):
            return str(self.personal.get("gender", "Prefer not to say"))
        if any(w in q for w in ["authorized", "visa", "work permit", "citizen"]):
            return "Yes"
        if any(w in q for w in ["sponsor", "sponsorship"]):
            return "No"
        if any(w in q for w in ["disability", "veteran"]):
            return "No"

        logger.warning(f"No answer found for question: '{question}' — using empty string")
        return ""

    def answer_numeric(self, question: str) -> str:
        ans = self.answer(question)
        numbers = re.findall(r"\d+", ans)
        return numbers[0] if numbers else "3"
