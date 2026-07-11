"""packs/climate_pack.py — Climate & Energy AI Intelligence Pack."""

from packs.base_pack import BasePack


class ClimatePack(BasePack):

    @property
    def domain_name(self) -> str:
        return "Climate & Energy AI"

    @property
    def arxiv_queries(self):
        return [
            {"name": "Carbon Capture AI", "query": 'all:"carbon capture" AND all:"machine learning"', "count": 10},
            {"name": "Energy Grid AI", "query": 'all:"smart grid" OR all:"energy storage" AND all:"deep learning"', "count": 10},
            {"name": "Climate Modeling", "query": 'all:"climate model" AND (all:"neural network" OR all:"AI")', "count": 10},
            {"name": "Renewable Energy Forecasting", "query": 'all:"solar energy" OR all:"wind power" AND all:"forecasting" AND all:"machine learning"', "count": 8},
            {"name": "Sustainable Materials", "query": 'all:"materials discovery" AND all:"machine learning"', "count": 8},
        ]

    @property
    def known_competitors(self):
        return [
            "Tomorrow.io", "ClimaCell", "Jupiter Intelligence",
            "Pachama", "Xpansiv", "South Pole", "Rocky Mountain Institute",
            "Watershed", "Persefoni", "Sweep",
        ]

    @property
    def known_regulations(self):
        return [
            "Paris Agreement", "EU Green Deal", "SEC Climate Disclosure",
            "CSRD", "Carbon Border Adjustment Mechanism (CBAM)",
            "Inflation Reduction Act (IRA)", "REACH"
        ]

    @property
    def key_economic_signals(self):
        return [
            "Carbon Price Rising ($50→$100/tonne trajectory)",
            "IRA Clean Energy Tax Credits ($369B)",
            "Corporate Net-Zero Commitments (90% of S&P 500)",
            "Energy Cost Volatility Post-Ukraine",
            "AI Compute Energy Footprint Scrutiny",
        ]

    @property
    def critic_kill_conditions(self):
        return [
            "REJECT if no connection to a measurable carbon or energy outcome",
            "REJECT if pure carbon offset marketplace (saturated)",
            "REJECT if requires regulatory regime not yet passed",
        ]
