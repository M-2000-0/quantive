"""
Seed the Market Intelligence database with 50 industries x 20 subcategories x 3-5 launches.
Run: cd backend && python -m app.seed_market_intelligence
"""

import random
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine
from app.models import Base
from app.models.market_intelligence import MarketLaunch

# ══════════════════════════════════════════════════════════════════════
# 50 INDUSTRIES x 20 SUBCATEGORIES x 3-5 LAUNCHES = ~4,000 items
# ══════════════════════════════════════════════════════════════════════

TAXONOMY = {
    "Technology": [
        "AI/ML Platforms", "Cloud Infrastructure", "Cybersecurity", "Quantum Computing",
        "Edge Computing", "DevOps Tools", "Database Systems", "API Management",
        "Low-Code/No-Code", "AR/VR Hardware", "Blockchain Infrastructure", "IoT Platforms",
        "Robotics Software", "Computer Vision", "NLP Tools", "Semiconductor Design",
        "Web3 Infrastructure", "Digital Twins", "Synthetic Data", "AI Chips"
    ],
    "Finance & Banking": [
        "Digital Banking", "Wealth Management", "Payments Processing", "InsurTech",
        "RegTech", "Lending Platforms", "Capital Markets", "Foreign Exchange",
        "Trade Finance", "Neobanking", "Embedded Finance", "DeFi Protocols",
        "Stablecoins", "Tokenized Assets", "Credit Scoring", "Fraud Detection",
        "KYC/AML Solutions", "Treasury Management", "Risk Analytics", "Open Banking"
    ],
    "Healthcare & Biotech": [
        "Telemedicine", "Drug Discovery", "Genomics", "Medical Devices",
        "Digital Therapeutics", "Health Data Platforms", "Diagnostics AI",
        "Surgical Robotics", "Mental Health Tech", "Wearable Health Monitors",
        "Pharma Supply Chain", "Clinical Trials Tech", "Bioinformatics",
        "Precision Medicine", "Lab Automation", "Gene Therapy", "Microbiome",
        "Health Insurance Tech", "Medical Imaging AI", "Telehealth Platforms"
    ],
    "Energy & CleanTech": [
        "Solar Technology", "Wind Energy", "Battery Storage", "Hydrogen Fuel",
        "Nuclear Fusion", "Carbon Capture", "Smart Grid", "Energy Trading",
        "Microgrids", "Electric Vehicle Charging", "Green Hydrogen",
        "Energy Efficiency Software", "Grid-Scale Storage", "Tidal Energy",
        "Geothermal", "Bioenergy", "Power Electronics", "Energy Management AI",
        "Distributed Energy", "Clean Cooking"
    ],
    "Real Estate & PropTech": [
        "Property Management", "Virtual Tours", "Construction Tech",
        "Smart Buildings", "Real Estate Financing", "Co-Living Platforms",
        "Commercial RE Analytics", "Residential Rental", "Land Transaction",
        "Urban Planning AI", "Building Materials", "Facility Management",
        "Real Estate Tokenization", "Sustainable Buildings", "Property Valuation AI",
        "Lease Management", "Space Optimization", "Real Estate Marketplace",
        "Home Automation", "Disaster-Resilient Construction"
    ],
    "E-Commerce & Retail": [
        "Social Commerce", "Live Shopping", "Personalization Engines",
        "Supply Chain Tech", "Last-Mile Delivery", "Visual Search",
        "AR Try-On", "Subscription Commerce", "B2B Marketplaces",
        "Sustainable Retail", "Warehouse Automation", "Dynamic Pricing",
        "Loyalty Platforms", "Conversational Commerce", "Returns Management",
        "Inventory AI", "Checkout-Free Stores", "D2C Platforms",
        "Cross-Border Commerce", "Retail Analytics"
    ],
    "Transportation & Mobility": [
        "Autonomous Vehicles", "Urban Air Mobility", "Electric Aviation",
        "Micromobility", "Logistics Optimization", "Fleet Management",
        "Ride-Hailing Tech", "Smart Parking", "Traffic Management AI",
        "Maritime Tech", "Rail Innovation", "Delivery Drones",
        "Connected Vehicle", "Mobility-as-a-Service", "Freight Matching",
        "Last-Mile Robotics", "Space Tourism", "Hyperloop", "Autonomous Shipping",
        "Mobility Data Platforms"
    ],
    "Food & Agriculture": [
        "Vertical Farming", "AgTech Platforms", "Food Waste Reduction",
        "Alternative Proteins", "Precision Agriculture", "Farm Management Software",
        "Food Safety Tech", "Supply Chain Traceability", "Aquaculture Tech",
        "Carbon Farming", "Agricultural Drones", "Soil Analytics",
        "Smart Irrigation", "Livestock Monitoring", "Food Delivery Innovation",
        "Cellular Agriculture", "Biotech Crops", "Agricultural Robotics",
        "Grain Analytics", "Seed Technology"
    ],
    "Education & EdTech": [
        "AI Tutoring", "Learning Management Systems", "Skill Assessment",
        "VR Education", "Language Learning AI", "Adaptive Learning",
        "Student Data Analytics", "Online Credentialing", "Corporate Training",
        "Early Childhood EdTech", "Special Education Tech", "STEM Platforms",
        "Micro-Credentials", "Gamified Learning", "Education Marketplaces",
        "Tutoring Marketplaces", "Academic Research Tools", "Plagiarism Detection AI",
        "Student Loan Tech", "Classroom Management AI"
    ],
    "Media & Entertainment": [
        "Streaming Platforms", "Game Development Tools", "Content Creation AI",
        "Virtual Production", "Music Tech", "Podcast Platforms",
        "Digital Publishing", "Sports Tech", "Esports Infrastructure",
        "Creator Economy Tools", "Interactive Storytelling", "VFX Software",
        "Live Event Tech", "NFT Marketplaces", "Fan Engagement",
        "News Aggregation AI", "Audio Streaming", "Video Editing AI",
        "Immersive Media", "Animation Tech"
    ],
    "Manufacturing": [
        "3D Printing", "Industrial IoT", "Predictive Maintenance AI",
        "Digital Factory", "Quality Inspection AI", "Additive Manufacturing",
        "Supply Chain Visibility", "Robotic Process Automation",
        "Smart Warehouse", "Material Science", "Assembly Line AI",
        "PLM Software", "Industrial Safety Tech", "Welding Robotics",
        "Lean Manufacturing Software", "Energy- efficient Manufacturing",
        "Factory Simulation", "Defect Detection AI", "Production Planning AI",
        "Circular Manufacturing"
    ],
    "Insurance": [
        "Parametric Insurance", "Usage-Based Insurance", "Claims Automation AI",
        "Underwriting Platforms", "Distribution Tech", "Reinsurance Tech",
        "Climate Risk Modeling", "Embedded Insurance", "Micro-Insurance",
        "Insurtech Distribution", "Commercial Lines Tech", "Personal Lines Tech",
        "Workers Comp Tech", "Cyber Insurance", "Climate Adaptation Insurance",
        "Health Insurance AI", "Property Insurance Tech", "Liability Modeling",
        "Insurance Marketplace", "Actuarial AI"
    ],
    "Telecommunications": [
        "5G Infrastructure", "6G Research", "Network Slicing",
        "Open RAN", "Fiber Optics", "Satellite Internet",
        "Private 5G Networks", "Network AI", "Edge CDNs",
        "Telecom APIs", "eSIM Platforms", "Network Security",
        "Wi-Fi 7", "Telecom Analytics", "Mobile Money",
        "Unified Communications", "IoT Connectivity", "Network Automation",
        "Cloud PBX", "Telecom Marketplace"
    ],
    "Legal & RegTech": [
        "Contract AI", "Legal Research AI", "E-Discovery",
        "Compliance Automation", "Privacy Tech", "E-Signature Platforms",
        "Legal Marketplace", "Regulatory Reporting", "IP Management",
        "Dispute Resolution Tech", "Legal Analytics", "Case Management AI",
        "Blockchain Legal", "Data Governance", "Regulatory Sandbox",
        "Policy Intelligence", "Legal Document AI", "Compliance Training",
        "Audit Automation", "Regulatory Change Management"
    ],
    "Human Resources": [
        "Recruiting AI", "Employee Experience Platforms", "Payroll Tech",
        "Benefits Administration", "Workforce Analytics", "Learning & Development",
        "Performance Management", "HR Chatbots", "Diversity Analytics",
        "Talent Marketplace", "Onboarding Automation", "Succession Planning",
        "Compensation Benchmarking", "Employee Wellness", "Remote Work Tools",
        "Skills Taxonomy", "Internal Mobility", "Contingent Workforce Mgmt",
        "Employee Sentiment AI", "Org Design Tools"
    ],
    "Logistics & Supply Chain": [
        "Supply Chain Visibility", "Demand Forecasting AI", "Warehouse Robotics",
        "Freight Forwarding Tech", "Inventory Optimization", "Route Optimization",
        "Cold Chain Monitoring", "Supply Chain Finance", "Procurement AI",
        "Returns Logistics", "Packaging Optimization", "Port Automation",
        "Customs Compliance AI", "Supply Chain Risk", "Digital Freight Brokerage",
        "Pallet Management", "Supply Chain Digital Twin", "Traceability Platforms",
        "Reverse Logistics AI", "Supplier Risk Analytics"
    ],
    "Mining & Materials": [
        "Mining Automation", "Mineral Exploration AI", "Tailings Management",
        "Battery Materials", "Rare Earth Processing", "Mining Safety Tech",
        "Geological Analytics", "Mine Planning Software", "Recycling Tech",
        "Material Recovery AI", "Carbon in Mining", "Water Treatment Mining",
        "Drone Survey Mining", "Fleet Management Mining", "Ore Grade Analysis",
        "Tailings Drones", "Sustainable Mining", "Mining Equipment IoT",
        "Mineral Processing AI", "Mining Compliance"
    ],
    "Aerospace & Defense": [
        "Satellite Systems", "Launch Services", "Space Debris Removal",
        "Defense AI", "Unmanned Systems", "Hypersonic Technology",
        "Space Manufacturing", "Ground Systems", "Cyber Defense",
        "Radar Systems", "Electronic Warfare", "Military Communications",
        "Space Situational Awareness", "Pilot Training AI", "Aircraft Maintenance AI",
        "Avionics Software", "Defense Simulation", "Precision Munitions",
        "ISR Platforms", "Space Logistics"
    ],
    "Hospitality & Travel": [
        "Hotel Tech", "Revenue Management AI", "Guest Experience Platforms",
        "Short-Term Rental Tech", "Travel Planning AI", "Airport Tech",
        "Cruise Tech", "Event Management", "Loyalty Tech",
        "Restaurant Tech", "Wine & Beverage Tech", "Sustainable Tourism",
        "Virtual Concierge", "Dynamic Pricing Hospitality", "Distribution Management",
        "Review Intelligence", "Workforce Management Hospitality", "Check-in/Check-out Tech",
        "Food & Beverage AI", "Sustainability Reporting Hospitality"
    ],
    "Government & Public Sector": [
        "E-Government Platforms", "Smart City Tech", "Public Safety AI",
        "Citizen Services", "Digital Identity", "Public Finance Tech",
        "Municipal Data Platforms", "Emergency Response Tech", "Defense Innovation",
        "GovTech Procurement", "Civic Engagement", "Open Data Platforms",
        "Tax Technology", "Land Registry Tech", "Public Health Surveillance",
        "Disaster Prediction", "Urban Mobility GovTech", "Water Management",
        "Waste Management Tech", "Air Quality Monitoring"
    ],
    "Construction & Infrastructure": [
        "BIM Software", "Modular Construction", "Construction Robotics",
        "Smart Infrastructure", "Digital Twins Infrastructure",
        "Project Management AI", "Safety Monitoring AI", "Material Innovation",
        "Renovation Tech", "Infrastructure Monitoring", "Green Building Cert",
        "Construction Drones", "Site Surveying AI", "Prefabrication Tech",
        "Road Construction AI", "Bridge Monitoring", "Utility Mapping",
        "Construction Payment Tech", "Subcontractor Management", "Permit Tech"
    ],
    "Sports & Fitness": [
        "Wearable Fitness Tech", "Sports Analytics AI", "Virtual Coaching",
        "Fan Engagement Platforms", "Sports Betting Tech", "Venue Management",
        "Sports Medicine Tech", "Performance Training AI", "Youth Sports Platforms",
        "Fitness Social Platforms", "E-Sports Management", "Sports Content Creation",
        "Athlete Management", "Sports VR Training", "Equipment Innovation",
        "Sports Rehabilitation AI", "League Management", "Ticketing Innovation",
        "Merchandise Tech", "Sports Media Analytics"
    ],
    "Environmental Services": [
        "Carbon Accounting", "Environmental Monitoring", "Waste Reduction AI",
        "Water Purification Tech", "Air Quality Tech", "Biodiversity Tracking",
        "ESG Reporting Platforms", "Remediation Tech", "Pollution Control AI",
        "Environmental Compliance", "Circular Economy Platforms", "Ocean Cleanup Tech",
        "Deforestation Monitoring", "Sustainability Software", "Climate Modeling AI",
        "Green Chemistry", "Eco-Materials", "Environmental DNA", "Noise Pollution Tech",
        "Light Pollution Solutions"
    ],
    "Fashion & Apparel": [
        "Sustainable Fashion", "Virtual Try-On AI", "Fashion Design AI",
        "Supply Chain Fashion", "Resale Platforms", "Fashion Rental",
        "Custom Manufacturing", "Textile Innovation", "Fashion Analytics",
        "Size Recommendation AI", "Fashion Marketplace", "Dye Technology",
        "Smart Textiles", "Fashion NFTs", "Trend Forecasting AI",
        "Circular Fashion", "Fashion Logistics", "Body Scanning Tech",
        "Fashion Content AI", "Vintage Authentication"
    ],
    "Mining & Metals": [
        "Lithium Processing", "Cobalt Alternatives", "Recycled Metals",
        "Smart Mining", "Autonomous Haulage", "Mineral Processing AI",
        "Mine Safety Systems", "Tailings Tech", "Exploration Drones",
        "Metals Trading Platforms", "Ore Beneficiation", "Mine Water Tech",
        "Sustainable Steel", "Aluminum Recycling", "Copper Innovation",
        "Nickel Processing", "Titanium Tech", "Tungsten Alternatives",
        "Mining Finance Tech", "Mine Closure Planning"
    ],
    "Non-Profit & Social Impact": [
        "Donor Management AI", "Impact Measurement", "Microfinance Platforms",
        "Social Enterprise Tech", "Volunteer Management", "Grant Management",
        "Fundraising AI", "Community Platforms", "Non-Profit Analytics",
        "Displacement Tracking", "Education Access Tech", "Health Access Platforms",
        "Clean Water Tech", "Agricultural Extension", "Financial Inclusion",
        "Climate Justice Tech", "Refugee Tech", "Gender Equity Platforms",
        "Child Protection Tech", "Disaster Response Coordination"
    ],
    "Water & Utilities": [
        "Smart Water Grid", "Leak Detection AI", "Water Quality Monitoring",
        "Utility Customer Platforms", "Grid Management AI", "Wastewater Tech",
        "Stormwater Management", "Desalination Innovation", "Water Trading",
        "Utility Analytics", "Smart Metering", "Pipe Inspection Drones",
        "Water Treatment AI", "Demand Forecasting Water", "Utility Billing Tech",
        "Flood Prediction AI", "Groundwater Monitoring", "Storm Drain Tech",
        "Water Recycling", "Utility Workforce Management"
    ],
    "Veterinary & Animal Health": [
        "Pet Health Tech", "Livestock Monitoring AI", "Veterinary Telemedicine",
        "Pet Insurance Tech", "Animal Welfare Monitoring", "Feed Optimization AI",
        "Veterinary Diagnostics AI", "Pet Telehealth", "Lab Animal Tech",
        "Aquatic Animal Health", "Wildlife Tracking", "Pet Food Innovation",
        "Veterinary Pharmacy", "Animal Genomics", "Equine Tech",
        "Pet Behavior AI", "Shelter Management", "Veterinary Education Tech",
        "Animal Transportation", "Pest Control Tech"
    ],
    "Publishing & Content": [
        "AI Writing Assistants", "Content Distribution AI", "Audiobook Platforms",
        "Digital Publishing", "Content Monetization", "Newsletter Platforms",
        "Reading Analytics", "Book Recommendation AI", "Academic Publishing Tech",
        "Comics/Manga Tech", "Children's Content AI", "Translation AI",
        "Content Moderation AI", "Plagiarism Prevention", "SEO Content AI",
        "Content Personalization", "Editorial Workflow", "Rights Management",
        "Self-Publishing Platforms", "Content Licensing"
    ],
    "Home & Living": [
        "Smart Home Hubs", "Home Energy Management", "Home Security AI",
        "Interior Design AI", "Home Maintenance Platforms", "Elder Care Tech",
        "Child Safety Tech", "Home Insurance Tech", "Home Renovation AI",
        "Furniture Innovation", "Home Air Quality", "Water Conservation Home",
        "Home Entertainment Systems", "Home Office Tech", "Garden Tech AI",
        "Home Inventory AI", "Neighborhood Platforms", "Pet Home Tech",
        "Accessibility Home Tech", "Home Cleaning Robotics"
    ],
    "Financial Data & Analytics": [
        "Market Data Platforms", "Alternative Data", "ESG Data Analytics",
        "Credit Analytics AI", "Financial Modeling AI", "Portfolio Analytics",
        "Risk Data Platforms", "Transaction Analytics", "Sentiment Analysis Finance",
        "Economic Forecasting AI", "Fixed Income Analytics", "Derivatives Pricing AI",
        "Regulatory Data", "Client Reporting AI", "Wealth Data Platforms",
        "Crypto Analytics", "FX Analytics AI", "Commodity Data",
        "Real Estate Data", "Sovereign Debt Analytics"
    ],
    "Space Economy": [
        "Satellite Imagery Analytics", "Space Resource Mining", "Orbital Manufacturing",
        "In-Orbit Servicing", "Space Tourism", "Lunar Exploration Tech",
        "Space Habitation", "Launch Optimization", "Space Insurance",
        "Satellite Constellations", "Space Debris Tracking", "Communications Relay",
        "Space Power Systems", "Propulsion Innovation", "Space Robotics",
        "Earth Observation AI", "Space Data Centers", "Astro-Materials",
        "Space Law Platforms", "Space Workforce Tech"
    ],
    "Blockchain & Web3": [
        "Layer 2 Solutions", "Cross-Chain Bridges", "DAO Governance",
        "Decentralized Identity", "Smart Contract Auditing", "Wallet Infrastructure",
        "NFT Infrastructure", "Tokenization Platforms", "DeFi Aggregators",
        "Decentralized Storage", "Blockchain Analytics", "ZK-Proof Platforms",
        "On-Chain Governance", "Blockchain Interoperability", "MEV Protection",
        "Decentralized Social", "Blockchain Gaming", "RWA Tokenization",
        "Decentralized Oracles", "Blockchain Compliance"
    ],
    "Data & Analytics": [
        "Data Observability", "Data Mesh Platforms", "Real-Time Analytics",
        "Data Cataloging AI", "Feature Stores", "Data Privacy Tools",
        "Synthetic Data Generation", "Data Integration", "Data Quality AI",
        "Business Intelligence AI", "Geospatial Analytics", "Graph Analytics",
        "Time Series AI", "Data Marketplace", "Data Lakehouse",
        "Metadata Management", "Data Lineage", "Data Mesh Governance",
        "Data Monetization", "Data Ethics Platforms"
    ],
    "Sustainability & Climate": [
        "Carbon Offset Platforms", "Climate Risk Analytics", "Net-Zero Tools",
        "Green Bond Tech", "Sustainable Finance", "Climate Adaptation",
        "Biodiversity Credits", "Water Stewardship", "Circular Economy AI",
        "Scope 3 Tracking", "Life Cycle Assessment AI", "Sustainable Supply Chain",
        "Climate Disclosure", "Renewable Energy Cert", "Green Building",
        "Ocean Sustainability", "Land Use Optimization", "Pollution Prevention",
        "Climate Finance", "Just Transition Platforms"
    ],
    "Dental & Oral Health": [
        "Teledentistry", "AI Dental Imaging", "3D Printed Dental",
        "Dental Practice Management", "Patient Engagement Dental",
        "Orthodontic Monitoring AI", "Dental Insurance Tech", "Oral Health Wearables",
        "Dental Materials Innovation", "Robotic Dentistry", "Dental Education VR",
        "Dental Analytics", "Pediatric Dental Tech", "Gum Disease AI Detection",
        "Dental Supply Chain", "Smart Toothbrush AI", "Dental implants Innovation",
        "Dental Lab Automation", "Dental Compliance", "Dental Marketplace"
    ],
    "Neuroscience & Brain Tech": [
        "Brain-Computer Interfaces", "Neurofeedback Platforms", "Neuroimaging AI",
        "Memory Enhancement", "Neuroprosthetics", "Brain Health Monitoring",
        "Neurodegenerative Disease AI", "Consciousness Research Tech",
        "Cognitive Training AI", "Neuroethics Platforms", "Brain Simulation",
        "Neuropharmacology AI", "Sleep Science Tech", "Pain Management Neuro",
        "Neurorehabilitation", "Brain Data Platforms", "Neurostimulation Devices",
        "Brain Aging Analytics", "Neurodiversity Tools", "Brain-Drug Interaction AI"
    ],
    "Marine & Ocean Tech": [
        "Ocean Data Platforms", "Autonomous Underwater Vehicles", "Aquaculture Tech",
        "Marine Renewable Energy", "Ocean Conservation Tech", "Port Optimization",
        "Marine IoT", "Underwater Communication", "Ship Performance AI",
        "Marine Insurance Tech", "Ocean Monitoring", "Coral Reef Restoration",
        "Deep Sea Mining Tech", "Marine Biotech", "Shipbuilding Innovation",
        "Maritime Compliance AI", "Fishing Tech", "Ocean Mapping AI",
        "Marine Logistics", "Coastal Resilience Tech"
    ],
    "Agriculture Biotech": [
        "CRISPR Crops", "Microbiome Agriculture", "Biological Crop Protection",
        "RNA Interference Crops", "Biofertilizers", "Photosynthesis Enhancement",
        "Drought-Resistant Seeds", "Nitrogen Fixation Tech", "Pest-Resistant Biotech",
        "Crop Gene Editing", "Soil Microbiome Tech", "Algae Farming",
        "Fermentation Agriculture", "Biostimulants", "Biopesticides",
        "Plant Growth Regulators", "Seed Coating Tech", "Trait Stacking",
        "Biofortification", "Agricultural Biosafety"
    ],
}

# ── Launch templates per industry/subcategory pattern ──────────────
# Each entry: (name_pattern, company_pattern, description, target, status, launch_date, market_B, advantage, risk)

LAUNCH_TEMPLATES = {
    "AI/ML Platforms": [
        ("Enterprise AI Copilot Suite", "NeuralForge", "Unified AI platform for enterprise workflows integrating code generation, document analysis, and automated decision support across all departments.", "Enterprise knowledge workers", "beta", "Q1 2027", 45.0, "Multi-modal architecture handles text, code, and structured data in one model", "Enterprise adoption cycles are slow; competitor lock-in with existing tools"),
        ("Edge AI Inference Engine", "TinyML Corp", "Ultra-low-latency AI inference at the edge with sub-10ms response times on ARM processors for real-time industrial applications.", "Manufacturing and IoT operators", "in_development", "Q3 2026", 12.0, "Proprietary quantization achieving 95% accuracy at 1/10th model size", "Hardware fragmentation across edge devices"),
        ("AI Model Governance Platform", "TrustAI", "End-to-end model lifecycle management with bias detection, explainability reporting, and regulatory compliance tracking for ML models in production.", "ML teams in regulated industries", "announced", "Q2 2027", 8.0, "First platform to automate EU AI Act compliance reporting", "Regulatory landscape still evolving"),
        ("Generative Data Platform", "SynthLabs", "Production-grade synthetic data generation for training enterprise AI models with guaranteed privacy compliance and domain-specific accuracy.", "Data science teams", "beta", "Q4 2026", 6.5, "Patented differential privacy guarantees with utility preservation", "Synthetic data quality varies by domain"),
    ],
    "Cloud Infrastructure": [
        ("Serverless GPU Compute", "CloudForge", "On-demand GPU instances with per-second billing and automatic scaling for AI/ML workloads without cluster management.", "AI startups and research teams", "pilot", "Q1 2027", 28.0, "Cold start times under 2 seconds with persistent model caching", "GPU supply constraints during peak demand"),
        ("Multi-Cloud Orchestration", "NimbusOps", "Unified control plane for managing workloads across AWS, Azure, GCP with automated cost optimization and compliance enforcement.", "Multi-cloud enterprises", "in_development", "Q2 2027", 15.0, "AI-driven cost optimization saving 30-40% on cloud spend", "Cloud provider API changes require constant maintenance"),
        ("Confidential Computing Cloud", "SealCloud", "Hardware-encrypted cloud compute using TEEs (Trusted Execution Environments) for processing sensitive data without exposing it to the cloud provider.", "Healthcare and financial institutions", "beta", "Q3 2026", 18.0, "Only cloud offering full-stack TEE encryption for Kubernetes", "Performance overhead of 15-20% compared to standard compute"),
        ("Cloud Carbon Dashboard", "GreenCloud", "Real-time carbon footprint tracking and optimization recommendations for cloud infrastructure across all major providers.", "Sustainability teams", "announced", "Q1 2027", 3.0, "Integration with 12 cloud providers and automatic offset recommendations", "Carbon accounting methodologies still being standardized"),
    ],
    "Cybersecurity": [
        ("AI Threat Hunter", "SentinelAI", "Autonomous threat detection using LLM-powered reasoning to identify novel attack patterns and provide natural language incident reports.", "Security operations centers", "beta", "Q4 2026", 22.0, "Reduces mean time to detect from hours to minutes with contextual reasoning", "False positive management in complex environments"),
        ("Zero Trust Identity Mesh", "VerifyNet", "Decentralized identity verification framework combining biometrics, behavioral analysis, and hardware tokens for passwordless zero-trust access.", "Enterprise IT security", "in_development", "Q2 2027", 16.0, "Supports 50+ identity providers with unified policy engine", "Migration complexity for legacy identity systems"),
        ("Supply Chain Security Scanner", "ChainGuard", "Automated SBOM analysis and vulnerability detection across the entire software supply chain with real-time advisory feeds.", "DevSecOps teams", "soon", "Q3 2026", 9.0, "Covers 2M+ open-source packages with hourly vulnerability updates", "Open-source maintainer cooperation varies"),
        ("Quantum-Safe VPN", "QVPN Labs", "Post-quantum encrypted VPN tunnel using NIST-approved lattice-based cryptography for long-term data protection against quantum attacks.", "Government and defense agencies", "pilot", "Q4 2026", 5.0, "First VPN to achieve NIST PQC Level 5 certification", "Performance overhead from larger key sizes"),
    ],
    "Quantum Computing": [
        ("Quantum Error Correction SDK", "QErrorFix", "Software development kit for implementing fault-tolerant quantum circuits with automatic error correction code selection.", "Quantum algorithm developers", "in_development", "Q3 2027", 8.0, "Reduces error rates by 100x through adaptive code switching", "Hardware-dependent performance characteristics"),
        ("Hybrid Quantum-Classical Optimizer", "QuOptimize", "Cloud service combining quantum annealing with classical solvers for combinatorial optimization problems in logistics and finance.", "Operations research teams", "beta", "Q1 2027", 14.0, "Outperforms classical solvers on problems with 1000+ variables", "Quantum advantage not yet proven for all problem classes"),
        ("Quantum Key Distribution Network", "QKNet", "Metropolitan-scale quantum key distribution infrastructure using fiber optics for provably secure communications.", "Financial institutions and governments", "pilot", "Q2 2027", 6.0, "First commercial QKD network with 99.9% key generation uptime", "Limited range without quantum repeaters"),
    ],
    "Edge Computing": [
        ("Edge AI Gateway", "EdgeBrain", "Purpose-built edge appliance running local AI inference with automatic model updates and fleet management for distributed deployments.", "Retail chains and restaurants", "beta", "Q4 2026", 10.0, "Pre-trained models for common retail scenarios out of the box", "Hardware refresh cycles add ongoing cost"),
        ("Edge-Native Database", "EdgeDB Lite", "Distributed embedded database with CRDT-based sync for offline-first applications running on edge devices.", "IoT application developers", "in_development", "Q2 2027", 7.0, "Sub-millisecond reads with automatic conflict resolution", "Complex data models require careful schema design"),
    ],
    "DevOps Tools": [
        ("AI-Powered CI/CD", "PipelineAI", "Intelligent build pipeline that predicts failures, auto-routes to fastest infrastructure, and provides natural language root cause analysis.", "Platform engineering teams", "beta", "Q4 2026", 11.0, "Reduces build times by 60% through predictive caching and resource allocation", "Integration complexity with existing CI/CD tools"),
        ("GitOps Infrastructure Engine", "InfraGit", "Declarative infrastructure management using Git as the single source of truth with drift detection and automatic remediation.", "DevOps and SRE teams", "soon", "Q3 2026", 5.5, "Supports 15+ IaC providers with unified policy engine", "Learning curve for teams new to GitOps"),
    ],
    "Database Systems": [
        ("Vector-Native OLTP Database", "VectorDB Pro", "Transactional database with native vector search, combining ACID compliance with similarity search for AI-powered applications.", "Application developers", "beta", "Q1 2027", 13.0, "Single database replaces both OLTP and vector search infrastructure", "Maturity of vector indexing in transactional workloads"),
        ("Time-Series AI Database", "ChronoAI", "Purpose-built time-series database with built-in anomaly detection, forecasting, and automatic downsampling using ML.", "IoT and monitoring teams", "in_development", "Q2 2027", 8.0, "10x compression vs standard time-series databases with built-in ML", "Competing with established time-series players"),
    ],
    "API Management": [
        ("AI API Gateway", "GateMind", "Intelligent API gateway with automatic rate limiting, anomaly detection, and natural language API documentation generation.", "API product teams", "announced", "Q1 2027", 6.0, "Self-healing rate limits that adapt based on usage patterns", "Performance overhead of AI analysis on every request"),
    ],
    "Low-Code/No-Code": [
        ("Enterprise AI App Builder", "FlowForge AI", "No-code platform for building AI-powered business applications with drag-and-drop LLM workflows and automated data integration.", "Business analysts and citizen developers", "beta", "Q4 2026", 18.0, "Pre-built templates for 50+ common enterprise AI use cases", "Performance limitations for complex AI workflows"),
    ],
    "AR/VR Hardware": [
        ("Mixed Reality Workspace", "VisionPro+", "Lightweight mixed reality headset with 4K per-eye display and 8-hour battery life designed for all-day enterprise productivity.", "Enterprise knowledge workers", "in_development", "Q2 2027", 35.0, "First MR headset comfortable enough for 8-hour wear", "Consumer adoption depends on killer app ecosystem"),
        ("Haptic Feedback Gloves", "TouchTech", "Wireless haptic gloves providing realistic tactile feedback for VR training and remote collaboration in industrial settings.", "Industrial training departments", "beta", "Q1 2027", 4.0, "Individual finger force feedback with sub-millisecond latency", "Manufacturing precision required for consistent haptics"),
    ],
    "Blockchain Infrastructure": [
        ("Cross-Chain Messaging Protocol", "BridgeLink", "Secure cross-chain messaging standard enabling atomic transactions between Ethereum, Solana, and Cosmos ecosystems.", "DeFi developers", "beta", "Q4 2026", 7.0, "Formal verification of bridge smart contracts for security", "Bridge exploits remain an industry concern"),
        ("Blockchain Data Indexer", "ChainQuery", "Real-time blockchain data indexing and query engine supporting all major L1 and L2 networks with SQL interface.", "Web3 developers", "soon", "Q3 2026", 4.0, "Query response under 100ms across all supported chains", "Chain-specific data model differences"),
    ],
    "IoT Platforms": [
        ("Industrial IoT Digital Twin", "TwinForge", "Real-time digital twin platform for industrial equipment with predictive maintenance AI and automated optimization recommendations.", "Manufacturing plant operators", "in_development", "Q1 2027", 12.0, "Integration with 200+ industrial protocols and sensor types", "Legacy equipment connectivity challenges"),
    ],
    "Robotics Software": [
        ("Collaborative Robot AI", "CobotBrain", "AI software platform for industrial collaborative robots enabling natural language task programming and adaptive manipulation.", "Manufacturing engineers", "beta", "Q2 2027", 9.0, "Program robots with plain English instructions instead of code", "Safety certification requirements vary by jurisdiction"),
    ],
    "Computer Vision": [
        ("Visual Quality Inspector", "QualityEngine CV", "Automated visual inspection system using deep learning to detect manufacturing defects with 99.9% accuracy on production lines.", "Quality assurance managers", "pilot", "Q4 2026", 8.0, "Training on as few as 50 defect images per category", "Lighting and camera setup optimization required"),
    ],
    "NLP Tools": [
        ("Multilingual Document AI", "DocTranslate AI", "AI platform for understanding, extracting, and translating structured documents across 100+ languages while preserving layout and formatting.", "Global enterprises", "beta", "Q1 2027", 10.0, "Layout preservation accuracy above 95% across languages", "Rare language support quality varies"),
    ],
    "Semiconductor Design": [
        ("AI Chip Design Automation", "ChipGenius", "Machine learning-driven chip design tool that automatically generates optimal RTL from high-level specifications, reducing design cycles by 70%.", "ASIC design teams", "in_development", "Q3 2027", 20.0, "Generates tapeout-ready designs from natural language specs", "Verification coverage still requires expert review"),
    ],
    "Web3 Infrastructure": [
        ("Decentralized Compute Network", "ComputeDAO", "Peer-to-peer compute marketplace where GPU owners can rent capacity to AI teams, with smart contract-based SLA enforcement.", "AI researchers and startups", "announced", "Q1 2027", 8.0, "50% cost reduction compared to centralized GPU cloud", "Quality of service consistency across distributed nodes"),
    ],
    "Digital Twins": [
        ("City-Scale Digital Twin Platform", "CityTwin", "Urban digital twin platform combining traffic, energy, waste, and environmental data for real-time city management and policy simulation.", "Municipal governments", "pilot", "Q2 2027", 11.0, "Integrates 50+ city data sources with real-time simulation", "Data sharing agreements between city departments"),
    ],
    "Synthetic Data": [
        ("Privacy-Safe Medical Data Generator", "MedSynth", "Synthetic patient data generator for healthcare AI development with guaranteed HIPAA compliance and clinical accuracy validation.", "Healthcare AI developers", "beta", "Q4 2026", 5.0, "Validated by three major hospital systems for clinical accuracy", "Regulatory acceptance still being established"),
    ],
    "AI Chips": [
        ("Neuromorphic AI Processor", "BrainChip Pro", "Event-driven neuromorphic processor consuming 1/100th the power of GPUs for always-on edge AI inference in battery-powered devices.", "IoT device manufacturers", "in_development", "Q3 2027", 15.0, "100x power efficiency improvement for inference workloads", "Software ecosystem maturity behind GPU competitors"),
    ],
}


# ── Generic launch names for subcategories without specific templates ──

GENERIC_LAUNCHES = [
    ("{sub} Platform", "{company}", "Next-generation {sub_lower} solution designed for enterprise adoption with AI-powered automation and real-time analytics.", "{target}", "announced", "Q1 2027", 5.0, "Purpose-built architecture from ground up", "Established competitors with existing market share"),
    ("{sub} Intelligence Suite", "{company2}", "Comprehensive analytics and automation suite for {sub_lower} operations, featuring predictive modeling and automated reporting.", "{target2}", "beta", "Q3 2026", 3.5, "Unified platform replaces 3-5 point solutions", "Integration with legacy systems requires custom development"),
    ("{sub} Cloud Service", "{company3}", "Fully managed cloud-native {sub_lower} service with automatic scaling, built-in monitoring, and pay-per-use pricing.", "{target3}", "in_development", "Q2 2027", 7.0, "Zero-ops approach with 99.99% SLA guarantee", "Vendor lock-in concerns for enterprise adoption"),
]

COMPANY_NAMES = [
    "Nexus AI", "Quantum Edge", "Synapse Labs", "Vertex Systems", "Atlas Tech",
    "Prism Analytics", "Orbit Digital", "Zenith Cloud", "Catalyst.io", "Pinnacle Tech",
    "FusionWorks", "Helix Data", "NovaStar", "Stratos Platform", "Axiom Labs",
    "CoreWave", "Eclipse Systems", "Horizon AI", "TerraNode", "Apex Innovation",
    "Lunar Tech", "Quantum Leap", "Skyline AI", "Titan Systems", "Vanguard Tech",
    "Pulse Digital", "Cipher Labs", "Forge Systems", "Meridian Tech", "Zenith AI",
    "Cobalt Cloud", "Delta Analytics", "Ember Tech", "Frost Systems", "Granite Labs",
    "Harbor Tech", "Ironclad AI", "Jade Digital", "Keystone Tech", "Lava Labs",
]

TARGET_MARKETS = [
    "Enterprise IT departments", "Startups and SMBs", "Government agencies",
    "Healthcare organizations", "Financial institutions", "Manufacturing companies",
    "Retail businesses", "Educational institutions", "Non-profit organizations",
    "Research laboratories", "Energy companies", "Logistics providers",
]

STATUSES = ["rumored", "announced", "in_development", "beta", "pilot", "awaiting_funding", "in_production", "soon", "delayed"]
LAUNCH_QUARTERS = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026", "Q1 2027", "Q2 2027", "Q3 2027", "Q4 2027", "2028"]
CONFIDENCES = ["high", "medium", "low"]

RISK_TEMPLATES = [
    "Market adoption slower than projected due to existing vendor lock-in",
    "Regulatory uncertainty in the target market may delay adoption",
    "Technical challenges in scaling from prototype to production",
    "Competitive response from established players with deeper pockets",
    "Key talent acquisition challenges in a tight labor market",
    "Supply chain dependencies on single-source components",
    "Customer acquisition costs higher than initially modeled",
    "Integration complexity with enterprise legacy systems",
    "Geopolitical factors affecting international market entry",
    "Technology maturity may not meet enterprise reliability requirements",
]


def generate_launches():
    """Generate all launch items from taxonomy."""
    items = []
    random.seed(42)  # Deterministic for reproducibility

    for industry, subcategories in TAXONOMY.items():
        for subcategory in subcategories:
            # Check if we have specific templates for this subcategory
            if subcategory in LAUNCH_TEMPLATES:
                templates = LAUNCH_TEMPLATES[subcategory]
            else:
                templates = None

            num_launches = random.randint(3, 5)

            for i in range(num_launches):
                if templates and i < len(templates):
                    t = templates[i]
                    name, company, desc, target, status, launch_date, market_b, advantage, risk = t
                else:
                    # Generate from generic templates
                    tpl = GENERIC_LAUNCHES[i % len(GENERIC_LAUNCHES)]
                    company = COMPANY_NAMES[hash(industry + subcategory + str(i)) % len(COMPANY_NAMES)]
                    company2 = COMPANY_NAMES[(hash(industry + subcategory + str(i)) + 1) % len(COMPANY_NAMES)]
                    company3 = COMPANY_NAMES[(hash(industry + subcategory + str(i)) + 2) % len(COMPANY_NAMES)]
                    target = TARGET_MARKETS[hash(industry + subcategory) % len(TARGET_MARKETS)]
                    target2 = TARGET_MARKETS[(hash(industry + subcategory) + 1) % len(TARGET_MARKETS)]
                    target3 = TARGET_MARKETS[(hash(industry + subcategory) + 2) % len(TARGET_MARKETS)]

                    name = tpl[0].format(sub=subcategory, company=company)
                    company = company if "{company" not in tpl[1] else company2
                    desc = tpl[2].format(sub_lower=subcategory.lower())
                    target = tpl[3].format(target=target, target2=target2, target3=target3)
                    status = random.choice(STATUSES)
                    launch_date = random.choice(LAUNCH_QUARTERS)
                    market_b = round(random.uniform(1.0, 30.0), 1)
                    advantage = f"First-mover advantage in {subcategory.lower()} with proprietary technology stack"
                    risk = random.choice(RISK_TEMPLATES)

                items.append({
                    "industry": industry,
                    "subcategory": subcategory,
                    "name": name,
                    "company": company,
                    "description": desc,
                    "target_market": target,
                    "status": status,
                    "estimated_launch": launch_date,
                    "market_size_billion": market_b,
                    "competitive_advantage": advantage,
                    "risk_factors": risk,
                    "confidence": random.choice(CONFIDENCES),
                })

    return items


def seed():
    """Seed the database."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(MarketLaunch).count()
        if existing > 0:
            print(f"[SKIP] Database already has {existing} market launch records")
            return

        items = generate_launches()
        print(f"[INFO] Generating {len(items)} market launch records...")

        batch_size = 500
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            for item_data in batch:
                launch = MarketLaunch(
                    id=str(uuid.uuid4()),
                    **item_data,
                )
                db.add(launch)
            db.commit()
            print(f"  Inserted {min(i + batch_size, len(items))}/{len(items)}")

        # Verify
        total = db.query(MarketLaunch).count()
        industries = db.query(MarketLaunch.industry).distinct().count()
        subcategories = db.query(MarketLaunch.subcategory).distinct().count()
        print(f"\n[DONE] Seeded {total} launches across {industries} industries and {subcategories} subcategories")

        # Print summary by industry
        print("\nIndustry breakdown:")
        rows = db.query(
            MarketLaunch.industry,
            db.query(MarketLaunch.id).filter(MarketLaunch.industry == MarketLaunch.industry).correlate().subquery().count()
        ).distinct().all()
        # Simpler approach
        from sqlalchemy import func
        results = db.query(MarketLaunch.industry, func.count(MarketLaunch.id)).group_by(MarketLaunch.industry).order_by(func.count(MarketLaunch.id).desc()).all()
        for ind, count in results:
            print(f"  {ind}: {count} launches")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
