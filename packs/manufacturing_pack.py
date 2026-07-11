"""packs/manufacturing_pack.py — Industrial AI & Manufacturing Intelligence Pack."""

from packs.base_pack import BasePack


class ManufacturingPack(BasePack):

    @property
    def domain_name(self) -> str:
        return "Industrial AI & Manufacturing"

    @property
    def arxiv_queries(self):
        return [
            {"name": "Predictive Maintenance", "query": 'all:"predictive maintenance" AND all:"machine learning"', "count": 12},
            {"name": "Process Optimization", "query": 'all:"process optimization" AND (all:"deep learning" OR all:"reinforcement learning")', "count": 10},
            {"name": "Supply Chain AI", "query": 'all:"supply chain" AND all:"AI" OR all:"demand forecasting" AND all:"machine learning"', "count": 10},
            {"name": "Quality Control Vision", "query": 'all:"quality control" AND all:"computer vision"', "count": 8},
            {"name": "Digital Twin", "query": 'all:"digital twin" AND all:"machine learning"', "count": 8},
        ]

    @property
    def known_competitors(self):
        return [
            "Uptake", "C3.ai", "Samsara", "Sight Machine",
            "SparkCognition", "Augury", "Aspentech", "GE Vernova",
            "Siemens MindSphere", "Rockwell Automation", "PTC ThingWorx",
        ]

    @property
    def known_regulations(self):
        return ["ISO 9001", "ISO 45001", "EU Machinery Regulation", "OSHA", "RoHS", "REACH"]

    @property
    def key_economic_signals(self):
        return [
            "Reshoring / Nearshoring trend ($300B US manufacturing investment)",
            "CHIPS Act ($52B semiconductor manufacturing)",
            "Industrial IoT sensor cost collapse",
            "Energy Cost Inflation (40% increase in 2022)",
            "Manufacturing Skills Gap (2.1M unfilled jobs by 2030)",
        ]

    @property
    def critic_kill_conditions(self):
        return [
            "REJECT if just a dashboard on top of existing SCADA/MES data",
            "REJECT if requires edge hardware deployment with no asset-light path",
            "REJECT if competing with Siemens/GE/Rockwell without specific vertical wedge",
        ]
