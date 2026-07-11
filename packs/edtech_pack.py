"""packs/edtech_pack.py — EdTech AI Intelligence Pack (original domain)."""

from packs.base_pack import BasePack


class EdtechPack(BasePack):

    @property
    def domain_name(self) -> str:
        return "EdTech AI"

    @property
    def arxiv_queries(self):
        return [
            {"name": "Special Education AI", "query": 'all:"special education" AND all:"AI"', "count": 10},
            {"name": "Adaptive Learning", "query": 'all:"adaptive learning" AND all:"machine learning"', "count": 10},
            {"name": "Knowledge Tracing", "query": 'all:"knowledge tracing" OR all:"student modeling"', "count": 8},
            {"name": "Assessment AI", "query": 'all:"automated grading" OR all:"essay scoring" AND all:"NLP"', "count": 8},
            {"name": "Vocational Training AI", "query": 'all:"vocational training" OR all:"skills training" AND all:"AI"', "count": 8},
        ]

    @property
    def known_competitors(self):
        return [
            "Khanmigo", "MagicSchool AI", "Turnitin", "Gradescope",
            "Carnegie Learning", "Duolingo", "Coursera", "Chegg",
            "IXL Learning", "Newsela", "Quizlet", "Brainly",
        ]

    @property
    def known_regulations(self):
        return ["FERPA", "COPPA", "GDPR", "EU AI Act", "CIPA", "IDEA (IEP mandates)"]

    @property
    def key_economic_signals(self):
        return [
            "Teacher Shortage (270,000 unfilled US positions)",
            "LLM Cost Drop (inference costs falling 90%)",
            "Post-COVID Learning Loss ($1.7T economic impact)",
            "AI-in-Education Market ($20B by 2027)",
            "GPT-4 release democratizing NLP for small EdTechs",
        ]

    @property
    def critic_kill_conditions(self):
        return [
            "REJECT if Khanmigo, MagicSchool, or Turnitin already does this",
            "REJECT if pure chatbot for homework with no pedagogy differentiation",
            "REJECT if requires K-12 district data sharing without FERPA clarity",
        ]
