"""Canonical map of optimized episode titles for SIB.

TITLES is used for YouTube and Spotify (no episode number — platforms show
it in their own UI). HUGO_TITLES adds a `#N` prefix for the website, which
doesn't have built-in episode numbering in the episode list.
"""

TITLES = {
    0: "The Pilot — Why We Started a Tech Podcast",
    1: "Zoom 10K Breakdown, Clubhouse & Microsoft Mesh AR/VR",
    2: "DraftKings 10K Breakdown — Kyle Schroeder & Nick Drost",
    3: "Snowflake 10K & Is Gartner Still Relevant? — Brad Murdoch",
    4: "Coinbase S1 Breakdown & Crypto — Kunal Anand, Imperva CTO",
    5: "Salesforce 10K Breakdown — Douglas Hanna, Grafana Labs COO",
    6: "Inside the Japanese IPO Market — Adrian Havill",
    7: "Peloton 10K Breakdown — Brent Holden, HashiCorp Field CTO",
    8: "5G Telco Deep Dive — Timo Jokiaho, Red Hat",
    9: "AI/ML & Sparse Computing — Brian Stevens, Neural Magic CEO",
    10: "ZoomInfo 10K Breakdown — Ben Sabrin, ngrok CRO",
    11: "Web3 & Blockchain Technologies — Forrest Colyer, AWS",
    12: "Empathy as a Service — Dr. Grin Lord, mpathic.ai CEO",
    13: "The NFT Deep Dive — Matthew Callahan, VaynerNFT",
    14: "Serverless Databases & Female Founders — Monica Sarbu, Xata",
    15: "Toll Brothers 10K Breakdown — Tota Mukherjee, Twilio",
    16: "Architecture & Innovation in Financial Services — Michael Russell",
    17: "AI Leadership & Analytics — Noelle Silver, IBM Partner",
    18: "VC Investing & Product Strategy — Gaurav Gupta, Lightspeed",
    19: "Crowd Forecasting & Collective Intelligence — Dr. Emile Servan-Schreiber",
    20: "Art, Estates & NFTs — Rory Trifon & Bobby Zeik",
    21: "Modernizing Sales & Go-to-Market — Eric Heikkila, Momento",
    22: "Hiring & WFH in the Digital-First World — Dawn Mitchell, HackerOne",
    23: "Leading with Influence in a Startup — Alex Francoeur, Xata",
    23.5: "AI Riff Interlude — Chad & Steve",
    24: "AI Sales Tools — William Dinkel, Nova.ai & Highspot",
    25: "SVB Collapse Analysis — Jason Apollo Voss, CFA",
    26: "Building Dev Tools at Scale — Rasmus Makwarth, Bucket & Opbeat",
    27: "Real-Time Data Streaming — Will LaForest, Confluent Field CTO",
    28: "Building Developer Communities — Stormy Peters, GitHub VP",
    29: "Building ClickHouse Cloud Pricing Model — Tanya Bragin, VP Product",
    30: "Predictive Analytics in Gambling — Earl Mitchell, Hard Rock Digital",
    31: "Buyer Enablement & Trust — Mark Green, Consensus",
    32: "Vector DBs & RAG — Matt Riley, Elastic VP of Search",
    33: "Marketing & Growth at Dev Tool Startups — Francesca Krihely-Price",
    34: "Semantic Search & RAG with LLMs — Shane Connelly, Vectara",
    35: "Unifying Batch & Streaming Data — Dr. Santona Tuli, Upsolver",
    36: "Tech Marketing from Elastic to Snyk — Jeff 'Yosh' Yoshimura",
    37: "Building Weaviate & Vector Search — Bob van Luijt, CEO",
    38: "Cloudflare & the Edge — John Engates, Field CTO",
    39: "The Fractional CTO Model — Alex Jukes",
    40: "Building Vectroid — Kevin Hanson, Co-Founder",
    41: "Unified Comms: Zoom to Illumy — Niel Levonius",
    42: "ClickHouse: Product & Growth — Tanya Bragin Returns",
    43: "AI for Real-World Physical Jobs — Jon Soini, ProofSight CEO",
    44: "From Tech to Dog Rescue — Ian Spandow",
    45: "Education & Leadership at Columbia — Dr. Roberta Lenger Kang",
}


def hugo_title(num, title: str) -> str:
    """Add #N prefix for Hugo (website episode list)."""
    if isinstance(num, float):
        return f"#{num} {title}"
    return f"#{num} {title}"


HUGO_TITLES = {num: hugo_title(num, t) for num, t in TITLES.items()}
