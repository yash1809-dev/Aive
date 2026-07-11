"""packs/healthcare_pack.py — Healthcare AI Intelligence Pack."""

from packs.base_pack import BasePack


class HealthcarePack(BasePack):

    @property
    def domain_name(self) -> str:
        return "Healthcare AI"

    @property
    def arxiv_queries(self):
        return [
            {"name": "Clinical Decision Support", "query": 'all:"clinical decision support" AND all:"machine learning"', "count": 15},
            {"name": "Medical NLP", "query": 'all:"clinical NLP" OR all:"biomedical NLP" AND all:"large language model"', "count": 12},
            {"name": "Drug Discovery AI", "query": 'all:"drug discovery" AND (all:"deep learning" OR all:"generative model")', "count": 12},
            {"name": "Radiology AI", "query": 'all:"radiology AI" OR all:"medical imaging" AND all:"deep learning"', "count": 10},
            {"name": "Mental Health AI", "query": 'all:"mental health" AND (all:"AI" OR all:"NLP" OR all:"LLM")', "count": 8},
        ]

    @property
    def known_competitors(self):
        return [
            "IBM Watson Health", "Google Health AI", "Microsoft Nuance",
            "Epic Systems", "Tempus AI", "PathAI", "Veracyte",
            "Butterfly Network", "Viz.ai", "Aidoc", "Enlitic",
        ]

    @property
    def known_regulations(self):
        return ["HIPAA", "FDA 510(k)", "CE Mark", "GDPR", "EU MDR", "HL7 FHIR"]

    @property
    def key_economic_signals(self):
        return [
            "Physician Burnout Crisis",
            "Prior Authorization Burden",
            "Healthcare Labor Shortage",
            "CMS Reimbursement Policy Changes",
            "LLM Cost Drop (inference costs falling 90%)",
        ]

    @property
    def critic_kill_conditions(self):
        return [
            "REJECT if requires FDA clearance with no regulatory path defined",
            "REJECT if no clear EHR integration pathway",
            "REJECT if competing with Epic/Oracle Health without clear wedge",
            "REJECT if clinical data access problem not addressed",
        ]
