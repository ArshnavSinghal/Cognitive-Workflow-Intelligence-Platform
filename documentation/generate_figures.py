"""
CWIP Figure Generation Script for Academic Minor Project Report
Generates 12 high-resolution, publication-quality figures representing the
actual implemented architecture, workflows, models, and schemas of CWIP.
"""

import os
import matplotlib
os.environ['MPLCONFIGDIR'] = os.path.abspath('documentation/figures/.mplconfig')
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = os.path.abspath('documentation/figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, '.mplconfig'), exist_ok=True)

# Styling parameters
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.5
plt.rcParams['figure.autolayout'] = True

# Colors
C_PRIMARY = '#1B365D'    # Dark Navy
C_SECONDARY = '#2980B9'  # Cerulean Blue
C_ACCENT = '#16A085'     # Deep Teal
C_ORANGE = '#D35400'     # Burnt Orange
C_GREEN = '#27AE60'      # Emerald Green
C_RED = '#C0392B'        # Crimson
C_BG_LIGHT = '#F8F9FA'   # Light Gray
C_BOX_BG = '#EBF5FB'     # Very Light Blue
C_BORDER = '#2C3E50'     # Dark Slate Border


# -------------------------------------------------------------
# Figure 1: CWIP System Architecture Overview
# -------------------------------------------------------------
def generate_fig1():
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 96, 'Figure 1: CWIP Multi-Tier Architecture Overview', 
            ha='center', va='center', fontsize=13, fontweight='bold', color=C_PRIMARY)

    # Tier 1: Presentation Layer
    rect1 = patches.FancyBboxPatch((4, 76), 92, 16, boxstyle="round,pad=1.5", 
                                   facecolor='#E8F8F5', edgecolor='#16A085', linewidth=1.5)
    ax.add_patch(rect1)
    ax.text(7, 88.5, 'PRESENTATION TIER (Frontend SPA)', fontsize=10.5, fontweight='bold', color='#0E6655')
    ax.text(50, 83.5, 'React 19 + Vite  |  Modular Component Hierarchy (App.jsx)  |  Lucide-React  |  Responsive CSS Grid\n'
                      'Active Views: Dynamic Overview Dashboard  •  Skill Catalogue & Enrollment  •  Prerequisite Profile Modal\n'
                      '6-Action Recommendation Surface  •  Learning Effectiveness Analytics  •  Platform Feedback Funnel',
            ha='center', va='center', fontsize=8.5, color='#17202A')

    # Arrow 1->2
    ax.annotate('', xy=(50, 71), xytext=(50, 76),
                arrowprops=dict(facecolor=C_PRIMARY, width=1.5, headwidth=7, shrink=0.05))
    ax.text(52, 73.5, 'REST API / JSON Payloads over HTTP (Bearer JWT)', fontsize=8, color='#5D6D7E')

    # Tier 2: Application / API Service Layer
    rect2 = patches.FancyBboxPatch((4, 48), 92, 22, boxstyle="round,pad=1.5", 
                                   facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=1.5)
    ax.add_patch(rect2)
    ax.text(7, 66.5, 'APPLICATION & API SERVICE TIER (FastAPI Backend)', fontsize=10.5, fontweight='bold', color='#1B4F72')
    
    # Internal submodules of Tier 2
    submodules = [
        ('API Gateway & Routers', 'FastAPI 0.162\nUvicorn ASGI\nAuto Swagger Docs\nCORS Middleware', 6, 50, 20, 13),
        ('Security & Auth', 'HTTPBearer Custom\nHS256 JWT Tokens\nStrict 401/403 Boundary\nRole-Based Access', 28, 50, 20, 13),
        ('Request Validation', 'Pydantic Schemas\nScore Bounding [0,100]\nFinite Number Checks\nCanonical Enums', 50, 50, 20, 13),
        ('Concurrency Engine', 'SQLAlchemy Session\nRow-Level Locking\n(SELECT FOR UPDATE)\nACID Transactions', 72, 50, 22, 13),
    ]
    for title, desc, x, y, w, h in submodules:
        sub_box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8",
                                         facecolor='#FFFFFF', edgecolor='#AED6F1', linewidth=1)
        ax.add_patch(sub_box)
        ax.text(x + w/2, y + h - 2.5, title, ha='center', va='center', fontsize=8, fontweight='bold', color=C_PRIMARY)
        ax.text(x + w/2, y + h/2 - 1.5, desc, ha='center', va='center', fontsize=7, color='#2C3E50')

    # Arrow 2->3
    ax.annotate('', xy=(50, 43), xytext=(50, 48),
                arrowprops=dict(facecolor=C_PRIMARY, width=1.5, headwidth=7, shrink=0.05))

    # Tier 3: Core Intelligence & Analytical Governance Layer
    rect3 = patches.FancyBboxPatch((4, 21), 92, 21, boxstyle="round,pad=1.5", 
                                   facecolor='#FEF9E7', edgecolor='#F39C12', linewidth=1.5)
    ax.add_patch(rect3)
    ax.text(7, 38.5, 'CORE INTELLIGENCE & MACHINE LEARNING TIER', fontsize=10.5, fontweight='bold', color='#7D6608')

    intel_modules = [
        ('NetworkX Graph Engine', 'DiGraph Prerequisite DAG\nBetweenness Centrality\nTopological Sort & Cycles\nBottleneck Diagnostics', 6, 23, 27, 12.5),
        ('Recommendation Policy', 'Scikit-learn Random Forest\n10 Engineered Features\n6 Canonical Actions (MIP)\nRemediation Decoupling', 35, 23, 29, 12.5),
        ('Statistical Governance', 'Step 4 Readiness Audit\nTrack A & B Partitions\nData Sufficiency Gates\nZero Leakage Enforcement', 66, 23, 28, 12.5),
    ]
    for title, desc, x, y, w, h in intel_modules:
        intel_box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8",
                                           facecolor='#FFFFFF', edgecolor='#FAD7A0', linewidth=1)
        ax.add_patch(intel_box)
        ax.text(x + w/2, y + h - 2.5, title, ha='center', va='center', fontsize=8, fontweight='bold', color='#7D6608')
        ax.text(x + w/2, y + h/2 - 1.5, desc, ha='center', va='center', fontsize=7, color='#2C3E50')

    # Arrow 3->4
    ax.annotate('', xy=(50, 16), xytext=(50, 21),
                arrowprops=dict(facecolor=C_PRIMARY, width=1.5, headwidth=7, shrink=0.05))

    # Tier 4: Persistence Tier
    rect4 = patches.FancyBboxPatch((4, 2), 92, 13, boxstyle="round,pad=1.5", 
                                   facecolor='#EAEDED', edgecolor='#7F8C8D', linewidth=1.5)
    ax.add_patch(rect4)
    ax.text(7, 11.5, 'PERSISTENCE TIER (Relational Storage)', fontsize=10.5, fontweight='bold', color='#34495E')
    ax.text(50, 6.5, 'PostgreSQL Relational Database  |  psycopg Driver  |  SQLAlchemy 2.0 ORM Mappings\n'
                      'Core Schemas: Users  •  Skills  •  Skill_Dependencies  •  Recommendation_Sessions  •  Activities  •  Learning_Outcomes\n'
                      'Integrity Guarantees: Foreign Key Cascades  •  Unique Constraint Indirection  •  B-Tree Foreign Indexes',
            ha='center', va='center', fontsize=8.2, color='#17202A')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig1_system_architecture.png'), dpi=300)
    plt.close()
    print("Saved fig1_system_architecture.png")


# -------------------------------------------------------------
# Figure 2: Closed-Loop Feedback Architecture
# -------------------------------------------------------------
def generate_fig2():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 2: Real-World Learning Data Collection & Feedback Loop Architecture', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    steps = [
        ('1. Session Generation', 'POST /skills/{id}/recommendation\nTarget & Remediation Decoupled\nStatus: Pending (Snapshot: M_pre)\nRF Action Policy Assigned', 6, 68, 26, 20, '#EBF5FB', '#2980B9'),
        ('2. Learner Execution', 'Learner engages recommended activity\nTracks Duration, Score, Errors\nAdherence Flag (Self-Reported)\nDirect vs Remediation Target', 37, 68, 26, 20, '#FEF9E7', '#F39C12'),
        ('3. Activity Logging', 'POST /activities (Linked Session)\nStrict Pydantic Input Validation\nRow-Level Locking (with_for_update)\nRace Condition Prevention', 68, 68, 26, 20, '#E8F8F5', '#16A085'),
        ('4. Mastery Recalculation', 'Atomic Session Attribution\nActivity-Driven Mastery Formula\nAuthoritative Post-Mastery (M_post)\nDelta Mastery: ΔM = M_post - M_pre', 68, 20, 26, 20, '#F4ECF7', '#8E44AD'),
        ('5. Outcome Creation', 'LearningOutcome Record Inserted\nServer-Controlled is_test Classification\nForeign Key Link to Parent Session\nSession Status -> Evaluated', 37, 20, 26, 20, '#FDEDEC', '#C0392B'),
        ('6. Governance Audit', 'Step 4 Evaluation Readiness Validator\nExclusion Filters & Sufficiency Gates\nTracks A & B Partitioning\nEmpirical Retraining Readiness', 6, 20, 26, 20, '#EAECEE', '#34495E'),
    ]

    for title, desc, x, y, w, h, bg, border in steps:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.2",
                                     facecolor=bg, edgecolor=border, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 3, title, ha='center', va='center', fontsize=8.8, fontweight='bold', color=border)
        ax.text(x + w/2, y + h/2 - 2, desc, ha='center', va='center', fontsize=7.5, color='#2C3E50')

    # Arrows between steps
    arrow_props = dict(facecolor=C_PRIMARY, width=1.5, headwidth=6, shrink=0.08)
    # 1 -> 2
    ax.annotate('', xy=(37, 78), xytext=(32, 78), arrowprops=arrow_props)
    # 2 -> 3
    ax.annotate('', xy=(68, 78), xytext=(63, 78), arrowprops=arrow_props)
    # 3 -> 4
    ax.annotate('', xy=(81, 40), xytext=(81, 68), arrowprops=arrow_props)
    # 4 -> 5
    ax.annotate('', xy=(63, 30), xytext=(68, 30), arrowprops=arrow_props)
    # 5 -> 6
    ax.annotate('', xy=(32, 30), xytext=(37, 30), arrowprops=arrow_props)
    # 6 -> 1 (Closed Feedback Loop)
    ax.annotate('', xy=(19, 68), xytext=(19, 40), arrowprops=arrow_props)
    ax.text(20.5, 54, 'Continuous Model\nEvolution & Audit', fontsize=7.5, color='#5D6D7E', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig2_feedback_loop.png'), dpi=300)
    plt.close()
    print("Saved fig2_feedback_loop.png")


# -------------------------------------------------------------
# Figure 3: Skill Dependency DAG
# -------------------------------------------------------------
def generate_fig3():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 3: Skill Dependency Directed Acyclic Graph (NetworkX DAG Model)', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    nodes = [
        ('Basic Probability\n(Node 1)', 15, 75, '#E8F8F5', '#16A085'),
        ('Descriptive Statistics\n(Node 2)', 15, 35, '#E8F8F5', '#16A085'),
        ('Statistical Foundations\n(Node 3 - Bottleneck)', 45, 55, '#FEF9E7', '#D35400'),
        ('Linear Regression\n(Node 4)', 80, 75, '#EBF5FB', '#2980B9'),
        ('Logistic Regression\n(Node 5)', 80, 55, '#EBF5FB', '#2980B9'),
        ('Multivariate Analytics\n(Node 6)', 80, 35, '#EBF5FB', '#2980B9'),
    ]

    for label, x, y, bg, border in nodes:
        box = patches.FancyBboxPatch((x-12, y-8), 24, 16, boxstyle="round,pad=1.2",
                                     facecolor=bg, edgecolor=border, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=8.2, fontweight='bold', color='#1A252F')

    # Edges: Prerequisite -> Dependent
    arrow_props = dict(facecolor='#2C3E50', width=1.4, headwidth=6, shrink=0.08)
    
    # 1 -> 3
    ax.annotate('', xy=(33, 58), xytext=(27, 72), arrowprops=arrow_props)
    ax.text(28, 67, 'w=0.85', fontsize=7.5, color='#7F8C8D')

    # 2 -> 3
    ax.annotate('', xy=(33, 52), xytext=(27, 38), arrowprops=arrow_props)
    ax.text(28, 43, 'w=0.90', fontsize=7.5, color='#7F8C8D')

    # 3 -> 4
    ax.annotate('', xy=(68, 73), xytext=(57, 60), arrowprops=arrow_props)
    ax.text(61, 69, 'w=0.80', fontsize=7.5, color='#7F8C8D')

    # 3 -> 5
    ax.annotate('', xy=(68, 55), xytext=(57, 55), arrowprops=arrow_props)
    ax.text(62, 57, 'w=0.75', fontsize=7.5, color='#7F8C8D')

    # 3 -> 6
    ax.annotate('', xy=(68, 38), xytext=(57, 50), arrowprops=arrow_props)
    ax.text(61, 42, 'w=0.82', fontsize=7.5, color='#7F8C8D')

    # Explanatory Box below
    rect_exp = patches.FancyBboxPatch((8, 6), 84, 16, boxstyle="round,pad=1.0",
                                      facecolor='#F8F9FA', edgecolor='#BDC3C7', linewidth=1)
    ax.add_patch(rect_exp)
    ax.text(50, 17, 'Graph Traversal & Bottleneck Analysis Rules (Edge Convention: Prerequisite -> Dependent)', 
            ha='center', va='center', fontsize=8.5, fontweight='bold', color=C_PRIMARY)
    ax.text(50, 11, '1. Predecessors = In-edges (Direct Prerequisites)  |  Successors = Out-edges (Direct Dependents)\n'
                    '2. Transitive Resolution: nx.ancestors(G, target) reveals all root dependencies across arbitrary hop depths\n'
                    '3. Multi-Hop Bottleneck Metric: B(p) = (1 - M_p) * w_p * (1 + 0.3 * OutDegree(p))  |  PageRank & Betweenness Centrality',
            ha='center', va='center', fontsize=7.6, color='#34495E')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig3_skill_graph.png'), dpi=300)
    plt.close()
    print("Saved fig3_skill_graph.png")


# -------------------------------------------------------------
# Figure 4: Level-0 Context DFD
# -------------------------------------------------------------
def generate_fig4():
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 4: Level-0 Context Data Flow Diagram (DFD)', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    # Central System Bubble
    circle = patches.Circle((50, 50), 16, facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=2)
    ax.add_patch(circle)
    ax.text(50, 52, '0.0\nCWIP SYSTEM', ha='center', va='center', fontsize=11, fontweight='bold', color='#1B4F72')
    ax.text(50, 42, 'Cognitive Workflow\nIntelligence Platform', ha='center', va='center', fontsize=7.5, color='#2C3E50')

    # External Entity 1: Learner
    box_l = patches.Rectangle((4, 38), 18, 24, facecolor='#E8F8F5', edgecolor='#16A085', linewidth=1.5)
    ax.add_patch(box_l)
    ax.text(13, 52, 'LEARNER\n(Student Actor)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#0E6655')

    # External Entity 2: Instructor / Admin
    box_i = patches.Rectangle((78, 38), 18, 24, facecolor='#FEF9E7', edgecolor='#F39C12', linewidth=1.5)
    ax.add_patch(box_i)
    ax.text(87, 52, 'INSTRUCTOR /\nADMINISTRATOR', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#7D6608')

    # Data flows Learner <-> CWIP
    arrow_props = dict(facecolor=C_PRIMARY, width=1.2, headwidth=5.5, shrink=0.05)
    # L -> CWIP (Top)
    ax.annotate('', xy=(34, 56), xytext=(22, 56), arrowprops=arrow_props)
    ax.text(28, 58.5, 'Registration, Enrollment,\nActivity Submissions', ha='center', va='bottom', fontsize=7.2, color='#2C3E50')
    # CWIP -> L (Bottom)
    ax.annotate('', xy=(22, 44), xytext=(34, 44), arrowprops=arrow_props)
    ax.text(28, 41.5, 'Personalized Recommendations,\nSkill Profiles, Effectiveness', ha='center', va='top', fontsize=7.2, color='#2C3E50')

    # Data flows CWIP <-> Instructor
    # CWIP -> I (Top)
    ax.annotate('', xy=(78, 56), xytext=(66, 56), arrowprops=arrow_props)
    ax.text(72, 58.5, 'Feedback Funnel Analytics,\nEvaluation Readiness Reports', ha='center', va='bottom', fontsize=7.2, color='#2C3E50')
    # I -> CWIP (Bottom)
    ax.annotate('', xy=(66, 44), xytext=(78, 44), arrowprops=arrow_props)
    ax.text(72, 41.5, 'Curriculum Skills, Graph\nPrerequisite Definitions', ha='center', va='top', fontsize=7.2, color='#2C3E50')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig4_dfd_level0.png'), dpi=300)
    plt.close()
    print("Saved fig4_dfd_level0.png")


# -------------------------------------------------------------
# Figure 5: Level-1 DFD Decomposition
# -------------------------------------------------------------
def generate_fig5():
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 97, 'Figure 5: Level-1 Data Flow Diagram (DFD) Decomposition', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    # Processes
    procs = [
        ('P1.0 Ingestion &\nValidation', 18, 72, '#EBF5FB', '#2980B9'),
        ('P2.0 Concurrency-Locked\nMastery Recalculation', 50, 72, '#E8F8F5', '#16A085'),
        ('P3.0 Transitive Graph\nDiagnosis (NetworkX)', 82, 72, '#FEF9E7', '#F39C12'),
        ('P4.0 Recommendation\nPolicy Synthesis (RF)', 82, 28, '#F4ECF7', '#8E44AD'),
        ('P5.0 Outcome Attribution\n& Session Finalization', 50, 28, '#FDEDEC', '#C0392B'),
        ('P6.0 Evaluation Readiness\nAudit & Partitioning', 18, 28, '#EAEDED', '#34495E'),
    ]

    for label, x, y, bg, border in procs:
        box = patches.FancyBboxPatch((x-14, y-9), 28, 18, boxstyle="round,pad=1.0",
                                     facecolor=bg, edgecolor=border, linewidth=1.4)
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', fontsize=8.2, fontweight='bold', color='#1C2833')

    # Data Stores (Open-ended parallel lines)
    stores = [
        ('D1: Users', 34, 91),
        ('D2: Skills & Dependencies', 66, 91),
        ('D3: Recommendation Sessions', 66, 9),
        ('D4: Activities & Outcomes', 34, 9),
    ]
    for sname, x, y in stores:
        ax.plot([x-12, x+12], [y+3, y+3], color='#566573', linewidth=1.5)
        ax.plot([x-12, x+12], [y-3, y-3], color='#566573', linewidth=1.5)
        ax.text(x, y, sname, ha='center', va='center', fontsize=7.8, fontweight='bold', color='#2C3E50')

    # Interconnecting arrows
    arrow = dict(facecolor=C_PRIMARY, width=1.1, headwidth=5, shrink=0.06)
    # P1 -> P2
    ax.annotate('', xy=(36, 72), xytext=(32, 72), arrowprops=arrow)
    ax.text(34, 75, 'Valid Activity', ha='center', fontsize=7, color='#5D6D7E')
    # P2 -> P3
    ax.annotate('', xy=(68, 72), xytext=(64, 72), arrowprops=arrow)
    ax.text(66, 75, 'Updated State', ha='center', fontsize=7, color='#5D6D7E')
    # P3 -> P4
    ax.annotate('', xy=(82, 37), xytext=(82, 63), arrowprops=arrow)
    ax.text(85, 50, 'Bottleneck Gap', ha='left', fontsize=7, color='#5D6D7E')
    # P4 -> P5
    ax.annotate('', xy=(64, 28), xytext=(68, 28), arrowprops=arrow)
    ax.text(66, 31, 'Action Policy', ha='center', fontsize=7, color='#5D6D7E')
    # P5 -> P6
    ax.annotate('', xy=(32, 28), xytext=(36, 28), arrowprops=arrow)
    ax.text(34, 31, 'Attributed Outcome', ha='center', fontsize=7, color='#5D6D7E')
    # P6 -> P1
    ax.annotate('', xy=(18, 63), xytext=(18, 37), arrowprops=arrow)
    ax.text(14, 50, 'Audit Filter', ha='right', fontsize=7, color='#5D6D7E')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig5_dfd_level1.png'), dpi=300)
    plt.close()
    print("Saved fig5_dfd_level1.png")


# -------------------------------------------------------------
# Figure 6: UML Use Case Diagram
# -------------------------------------------------------------
def generate_fig6():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 6: UML Use Case Diagram', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    # Boundary Box
    bound = patches.Rectangle((20, 4), 60, 88, facecolor='#FFFFFF', edgecolor='#34495E', linewidth=1.5, linestyle='--')
    ax.add_patch(bound)
    ax.text(50, 89, 'CWIP Core Platform Boundary', ha='center', va='center', fontsize=9, fontweight='bold', color='#7F8C8D')

    # Actors
    # Learner (Left)
    ax.plot([10, 10], [52, 60], color='#16A085', linewidth=2)  # Body
    c1 = patches.Circle((10, 63), 3, facecolor='#FFFFFF', edgecolor='#16A085', linewidth=2)  # Head
    ax.add_patch(c1)
    ax.plot([4, 16], [56, 56], color='#16A085', linewidth=2)   # Arms
    ax.plot([10, 6], [52, 44], color='#16A085', linewidth=2)   # Left Leg
    ax.plot([10, 14], [52, 44], color='#16A085', linewidth=2)  # Right Leg
    ax.text(10, 39, 'Learner', ha='center', va='top', fontsize=9, fontweight='bold', color='#0E6655')

    # Instructor / Admin (Right)
    ax.plot([90, 90], [52, 60], color='#F39C12', linewidth=2)  # Body
    c2 = patches.Circle((90, 63), 3, facecolor='#FFFFFF', edgecolor='#F39C12', linewidth=2)  # Head
    ax.add_patch(c2)
    ax.plot([84, 96], [56, 56], color='#F39C12', linewidth=2)   # Arms
    ax.plot([90, 86], [52, 44], color='#F39C12', linewidth=2)   # Left Leg
    ax.plot([90, 94], [52, 44], color='#F39C12', linewidth=2)   # Right Leg
    ax.text(90, 39, 'Instructor / Admin', ha='center', va='top', fontsize=9, fontweight='bold', color='#7D6608')

    # Use Cases (Ellipses)
    ucs = [
        ('Enroll in Skills & Browse Catalogue', 50, 81),
        ('View Skill Profile & Prerequisite Graph', 50, 68),
        ('Request Canonical Learning Recommendation', 50, 55),
        ('Submit Activity & Trigger Closed Feedback', 50, 42),
        ('Inspect Learning Effectiveness Analytics', 50, 29),
        ('Audit Evaluation Readiness & Platform Funnel', 50, 16),
    ]

    for text, cx, cy in ucs:
        ell = patches.Ellipse((cx, cy), 34, 9, facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=1.2)
        ax.add_patch(ell)
        ax.text(cx, cy, text, ha='center', va='center', fontsize=7.6, color='#1B4F72', fontweight='bold')

    # Connections Learner -> UCs (first 5)
    for i in range(5):
        cy = ucs[i][1]
        ax.plot([14, 33], [52, cy], color='#16A085', linewidth=1, linestyle=':')

    # Connections Admin -> UCs (all, especially last 2)
    ax.plot([86, 67], [52, 81], color='#F39C12', linewidth=1, linestyle=':')
    ax.plot([86, 67], [52, 29], color='#F39C12', linewidth=1, linestyle=':')
    ax.plot([86, 67], [52, 16], color='#F39C12', linewidth=1, linestyle=':')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig6_uml_use_case.png'), dpi=300)
    plt.close()
    print("Saved fig6_uml_use_case.png")


# -------------------------------------------------------------
# Figure 7: UML Class Diagram
# -------------------------------------------------------------
def generate_fig7():
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 97, 'Figure 7: UML Class Diagram (Domain Models, ORM Mappings & Service Layer)', 
            ha='center', va='center', fontsize=12, fontweight='bold', color=C_PRIMARY)

    classes = [
        ('User (ORM)', '+ id: int (PK)\n+ email: str (Unique)\n+ hashed_password: str\n+ full_name: str\n+ role: str\n+ is_active: bool\n+ created_at: datetime', 5, 52, 26, 40, '#EBF5FB', '#2980B9'),
        ('Skill (ORM)', '+ id: int (PK)\n+ name: str (Unique)\n+ description: str\n+ category: str\n+ difficulty_level: int\n+ created_at: datetime', 37, 52, 26, 40, '#E8F8F5', '#16A085'),
        ('SkillDependency (ORM)', '+ id: int (PK)\n+ parent_skill_id: int (FK)\n+ child_skill_id: int (FK)\n+ dependency_strength: float\n+ created_at: datetime', 69, 52, 26, 40, '#FEF9E7', '#F39C12'),
        ('RecommendationSession', '+ id: int (PK)\n+ user_id: int (FK)\n+ skill_id: int (FK)\n+ target_skill_id: int\n+ recommended_action: str\n+ pre_mastery: float\n+ status: str (pending/eval)', 5, 4, 26, 42, '#FDEDEC', '#C0392B'),
        ('Activity (ORM)', '+ id: int (PK)\n+ user_id: int (FK)\n+ skill_id: int (FK)\n+ activity_type: str\n+ duration_minutes: int\n+ score: float [0,100]\n+ errors_count: int', 37, 4, 26, 42, '#F4ECF7', '#8E44AD'),
        ('LearningOutcome (ORM)', '+ id: int (PK)\n+ recommendation_session_id (FK)\n+ activity_id: int (FK)\n+ delta_mastery: float\n+ is_test: bool\n+ is_adherent: bool', 69, 4, 26, 42, '#EAEDED', '#34495E'),
    ]

    for title, attrs, x, y, w, h, bg, border in classes:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8",
                                     facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(box)
        # Class Header
        ax.plot([x, x+w], [y+h-6, y+h-6], color=border, linewidth=1)
        ax.text(x + w/2, y + h - 3.5, title, ha='center', va='center', fontsize=8.2, fontweight='bold', color=border)
        # Attributes
        ax.text(x + 2, y + h - 8, attrs, ha='left', va='top', fontsize=6.8, color='#2C3E50', family='monospace')

    # Association lines
    ax.plot([31, 37], [72, 72], color='#2C3E50', linewidth=1.2)  # User -> Skill (Enrollment)
    ax.plot([63, 69], [72, 72], color='#2C3E50', linewidth=1.2)  # Skill -> Dependency
    ax.plot([18, 18], [52, 46], color='#2C3E50', linewidth=1.2)  # User -> Session
    ax.plot([50, 50], [52, 46], color='#2C3E50', linewidth=1.2)  # Skill -> Activity
    ax.plot([31, 37], [25, 25], color='#2C3E50', linewidth=1.2)  # Session -> Activity
    ax.plot([63, 69], [25, 25], color='#2C3E50', linewidth=1.2)  # Activity -> Outcome

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig7_uml_class.png'), dpi=300)
    plt.close()
    print("Saved fig7_uml_class.png")


# -------------------------------------------------------------
# Figure 8: UML Sequence Diagram
# -------------------------------------------------------------
def generate_fig8():
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 97, 'Figure 8: UML Sequence Diagram — Recommendation Generation & Feedback Loop', 
            ha='center', va='center', fontsize=12, fontweight='bold', color=C_PRIMARY)

    lifelines = [
        ('Client Browser\n(React 19)', 12),
        ('FastAPI Router\n(main.py)', 35),
        ('Recommendation\nEngine', 58),
        ('PostgreSQL DB\n(with_for_update)', 85),
    ]

    for name, x in lifelines:
        box = patches.FancyBboxPatch((x-9, 87), 18, 7, boxstyle="round,pad=0.5",
                                     facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=1.2)
        ax.add_patch(box)
        ax.text(x, 90.5, name, ha='center', va='center', fontsize=7.2, fontweight='bold', color='#1B4F72')
        # Lifeline dash
        ax.plot([x, x], [87, 8], color='#BDC3C7', linestyle='--', linewidth=1)

    # Sequence Messages
    msgs = [
        (12, 35, 80, 'POST /skills/{id}/recommendation', True),
        (35, 58, 72, 'extract_features() & diagnose_prerequisites()', True),
        (58, 58, 64, 'predict_action() -> Canonical Enum', False),
        (58, 85, 56, 'INSERT RecommendationSession (pending)', True),
        (85, 35, 48, 'Session ID & Snapshot Confirmed', False),
        (35, 12, 40, 'HTTP 200: Recommendation Payload', False),
        (12, 35, 32, 'POST /activities (with session_id & score)', True),
        (35, 85, 24, 'SELECT ... FOR UPDATE (Row Locking)', True),
        (85, 35, 16, 'Atomically Insert Activity & LearningOutcome', False),
        (35, 12, 9, 'HTTP 200: Feedback Loop Closed', False),
    ]

    for x1, x2, y, text, is_call in msgs:
        if x1 == x2:
            # Self call
            ax.plot([x1, x1+5, x1+5, x1], [y+2, y+2, y-2, y-2], color=C_PRIMARY, linewidth=1.2)
            ax.text(x1+6, y, text, ha='left', va='center', fontsize=7, color='#2C3E50')
        else:
            style = dict(facecolor=C_PRIMARY, width=1.0, headwidth=5, shrink=0.04)
            ax.annotate('', xy=(x2, y), xytext=(x1, y), arrowprops=style)
            ax.text((x1+x2)/2, y+1.8, text, ha='center', va='bottom', fontsize=7, color='#2C3E50')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig8_uml_sequence.png'), dpi=300)
    plt.close()
    print("Saved fig8_uml_sequence.png")


# -------------------------------------------------------------
# Figure 9: Relational Database ER Diagram
# -------------------------------------------------------------
def generate_fig9():
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 97, 'Figure 9: Relational Database Entity-Relationship (ER) Diagram', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    tables = [
        ('USERS', ['user_id (PK)', 'email (UQ)', 'password_hash', 'full_name', 'role'], 8, 55, 22, 34, '#E8F8F5', '#16A085'),
        ('SKILLS', ['skill_id (PK)', 'name (UQ)', 'category', 'difficulty', 'created_at'], 40, 55, 22, 34, '#FEF9E7', '#F39C12'),
        ('SKILL_DEPENDENCIES', ['dep_id (PK)', 'parent_skill_id (FK)', 'child_skill_id (FK)', 'dependency_strength'], 72, 55, 24, 34, '#EBF5FB', '#2980B9'),
        ('RECOMMENDATION_SESSIONS', ['session_id (PK)', 'user_id (FK)', 'skill_id (FK)', 'action_code', 'pre_mastery', 'status'], 8, 8, 26, 36, '#FDEDEC', '#C0392B'),
        ('ACTIVITIES', ['activity_id (PK)', 'user_id (FK)', 'skill_id (FK)', 'activity_type', 'score', 'duration'], 40, 8, 22, 36, '#F4ECF7', '#8E44AD'),
        ('LEARNING_OUTCOMES', ['outcome_id (PK)', 'session_id (FK)', 'activity_id (FK)', 'delta_mastery', 'is_test', 'is_adherent'], 70, 8, 26, 36, '#EAEDED', '#34495E'),
    ]

    for title, cols, x, y, w, h, bg, border in tables:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8",
                                     facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(box)
        # Header
        ax.plot([x, x+w], [y+h-6, y+h-6], color=border, linewidth=1)
        ax.text(x + w/2, y + h - 3.5, title, ha='center', va='center', fontsize=8, fontweight='bold', color=border)
        # Column list
        col_text = '\n'.join([f"• {c}" for c in cols])
        ax.text(x + 2, y + h - 9, col_text, ha='left', va='top', fontsize=7, color='#2C3E50', family='monospace')

    # Relationship connectors
    ax.plot([19, 19], [55, 44], color='#2C3E50', linewidth=1.2)  # Users -> Sessions (1:N)
    ax.plot([51, 51], [55, 44], color='#2C3E50', linewidth=1.2)  # Skills -> Activities (1:N)
    ax.plot([62, 72], [72, 72], color='#2C3E50', linewidth=1.2)  # Skills -> Dependencies (1:N)
    ax.plot([34, 40], [24, 24], color='#2C3E50', linewidth=1.2)  # Sessions -> Activities
    ax.plot([62, 70], [24, 24], color='#2C3E50', linewidth=1.2)  # Activities -> Outcomes (1:1)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig9_er_diagram.png'), dpi=300)
    plt.close()
    print("Saved fig9_er_diagram.png")


# -------------------------------------------------------------
# Figure 10: ML Partitioning Strategy
# -------------------------------------------------------------
def generate_fig10():
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 10: ML Pipeline & Dual-Track Partitioning Strategy', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    # Track A
    rect_a = patches.FancyBboxPatch((4, 48), 92, 42, boxstyle="round,pad=1.2",
                                    facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=1.4)
    ax.add_patch(rect_a)
    ax.text(7, 86, 'TRACK A: DISJOINT LEARNER CLUSTERS (GroupKFold Partitioning)', fontsize=9.5, fontweight='bold', color='#1B4F72')
    ax.text(7, 81, 'Evaluates generalizability across entirely unseen learner cohorts without cross-learner contamination.', fontsize=7.8, color='#2C3E50')

    # Folds visualization
    for i in range(5):
        fx = 8 + i * 18
        box_train = patches.Rectangle((fx, 54), 16, 22, facecolor='#AED6F1', edgecolor='#2980B9')
        ax.add_patch(box_train)
        if i == 4:
            box_test = patches.Rectangle((fx, 54), 16, 22, facecolor='#E74C3C', edgecolor='#922B21')
            ax.add_patch(box_test)
            ax.text(fx+8, 65, f'Fold {i+1}\nHeld-Out Test\n(Unseen Users)', ha='center', va='center', fontsize=7, color='#FFFFFF', fontweight='bold')
        else:
            ax.text(fx+8, 65, f'Fold {i+1}\nTrain Cluster\n(Learners {i*20}-{(i+1)*20})', ha='center', va='center', fontsize=7, color='#1B4F72')

    # Track B
    rect_b = patches.FancyBboxPatch((4, 4), 92, 40, boxstyle="round,pad=1.2",
                                    facecolor='#FEF9E7', edgecolor='#F39C12', linewidth=1.4)
    ax.add_patch(rect_b)
    ax.text(7, 40, 'TRACK B: CHRONOLOGICAL TEMPORAL SPLIT (Zero Future Leakage)', fontsize=9.5, fontweight='bold', color='#7D6608')
    ax.text(7, 35, 'Simulates real-world production deployment: historical outcomes predict future outcomes strictly in sequence.', fontsize=7.8, color='#2C3E50')

    # Timeline bar
    ax.plot([10, 90], [20, 20], color='#7F8C8D', linewidth=4)
    # Split point
    ax.plot([65, 65], [12, 28], color='#C0392B', linewidth=2.5, linestyle='--')
    ax.text(65, 30, 'Temporal Cutoff: T_split (70% Historical)', ha='center', fontsize=7.8, fontweight='bold', color='#C0392B')

    # Train portion
    rect_t_train = patches.Rectangle((10, 15), 55, 10, facecolor='#27AE60', alpha=0.3)
    ax.add_patch(rect_t_train)
    ax.text(37, 20, 'HISTORICAL TRAINING WINDOW (T < T_split)', ha='center', va='center', fontsize=8, fontweight='bold', color='#145A32')

    # Test portion
    rect_t_test = patches.Rectangle((65, 15), 25, 10, facecolor='#E74C3C', alpha=0.3)
    ax.add_patch(rect_t_test)
    ax.text(77.5, 20, 'FUTURE TEST WINDOW (T >= T_split)', ha='center', va='center', fontsize=8, fontweight='bold', color='#78281F')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig10_ml_partitioning.png'), dpi=300)
    plt.close()
    print("Saved fig10_ml_partitioning.png")


# -------------------------------------------------------------
# Figure 11: Statistical Evaluation Readiness Gates
# -------------------------------------------------------------
def generate_fig11():
    fig, ax = plt.subplots(figsize=(10, 5.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 96, 'Figure 11: Statistical Evaluation Readiness Gates & Sufficiency Funnel', 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color=C_PRIMARY)

    gates = [
        ('Gate 1: Total Real Outcomes (N >= 30 Minimal, N >= 150 Target)', 80, 85, '#EBF5FB', '#2980B9'),
        ('Gate 2: Unique Genuine Learners (K >= 15 Minimal Diversity)', 70, 71, '#E8F8F5', '#16A085'),
        ('Gate 3: Action Class Diversity (>= 2 Active Canonical Actions)', 60, 57, '#FEF9E7', '#F39C12'),
        ('Gate 4: Minimum Action Support (>= 3 Actions with >= 20 Outcomes Each)', 50, 43, '#F4ECF7', '#8E44AD'),
        ('Gate 5: Evaluation Set Size (K_eval >= 20 Distinct Test Learners)', 40, 29, '#FDEDEC', '#C0392B'),
        ('Gate 6: Calibration Set Sufficiency (K_cal,a >= 19 Observations per Action)', 30, 15, '#EAEDED', '#34495E'),
    ]

    for title, width, cy, bg, border in gates:
        rect = patches.FancyBboxPatch((50 - width/2, cy-5), width, 10, boxstyle="round,pad=0.8",
                                      facecolor=bg, edgecolor=border, linewidth=1.4)
        ax.add_patch(rect)
        ax.text(50, cy, title, ha='center', va='center', fontsize=8, fontweight='bold', color=border)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig11_evaluation_gates.png'), dpi=300)
    plt.close()
    print("Saved fig11_evaluation_gates.png")


# -------------------------------------------------------------
# Figure 12: React 19 Frontend Dashboard Component Architecture
# -------------------------------------------------------------
def generate_fig12():
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    ax.text(50, 97, 'Figure 12: React 19 Frontend Dashboard Component Hierarchy & UI State', 
            ha='center', va='center', fontsize=12, fontweight='bold', color=C_PRIMARY)

    # Root App Component
    root = patches.FancyBboxPatch((35, 83), 30, 10, boxstyle="round,pad=1.0",
                                  facecolor='#EBF5FB', edgecolor='#2980B9', linewidth=1.5)
    ax.add_patch(root)
    ax.text(50, 88, 'App.jsx (Root Controller)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#1B4F72')
    ax.text(50, 85, 'Auth State  •  Tab Navigation  •  Notification Banners', ha='center', va='center', fontsize=7, color='#2C3E50')

    # Navigation Tabs (5 Views)
    views = [
        ('Overview Tab', 'Adherence KPI Card\nOutcomes Counter\nEnrolled Progress', 6, 48, 16, 24, '#E8F8F5', '#16A085'),
        ('Skills Catalogue', 'Enrolled vs Available\nOne-Click Enrollment\nProfile Modal Trigger', 24.5, 48, 16, 24, '#FEF9E7', '#F39C12'),
        ('Recommendations', '6 Canonical Actions\nTarget vs Remediation\nMastery Deficit Metric', 43, 48, 16, 24, '#FDEDEC', '#C0392B'),
        ('Effectiveness', 'Delta Mastery Breakdowns\nAdherent vs Non-Adherent\nObservational Notice', 61.5, 48, 16, 24, '#F4ECF7', '#8E44AD'),
        ('Feedback Funnel', 'Conversion Conversion\nStep 4 Readiness Counters\nPlatform Observability', 80, 48, 16, 24, '#EAEDED', '#34495E'),
    ]

    for title, desc, x, y, w, h, bg, border in views:
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8",
                                     facecolor=bg, edgecolor=border, linewidth=1.2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 3.5, title, ha='center', va='center', fontsize=8, fontweight='bold', color=border)
        ax.text(x + w/2, y + h/2 - 2, desc, ha='center', va='center', fontsize=6.8, color='#2C3E50')
        # Connector from Root
        ax.plot([50, x + w/2], [83, y + h], color='#BDC3C7', linewidth=1, linestyle='--')

    # Modals & Service Layer (Bottom)
    modal_box = patches.FancyBboxPatch((6, 12), 42, 24, boxstyle="round,pad=1.0",
                                       facecolor='#FFFFFF', edgecolor='#16A085', linewidth=1.2)
    ax.add_patch(modal_box)
    ax.text(27, 31, 'SkillProfileModal Component', ha='center', va='center', fontsize=8.5, fontweight='bold', color='#0E6655')
    ax.text(27, 21, 'Empirical Mastery, Confidence, Trend Statistics\n'
                    'Activity History & Transactional Outcomes Breakdown\n'
                    'Prerequisite & Descendant Intelligence Graph Subpanel\n'
                    'Transitive Path Resolution & Bottleneck Explanations',
            ha='center', va='center', fontsize=7.2, color='#2C3E50')

    api_box = patches.FancyBboxPatch((52, 12), 44, 24, boxstyle="round,pad=1.0",
                                     facecolor='#FFFFFF', edgecolor='#2980B9', linewidth=1.2)
    ax.add_patch(api_box)
    ax.text(74, 31, 'api.js (REST API Client Layer)', ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1B4F72')
    ax.text(74, 21, 'fetchWithAuth() Wrapper  •  Auto Bearer Token Injection\n'
                    'Strict Error Handling: 401 Session Expiry vs 403 Forbidden\n'
                    'Endpoints: getOverview, getSkills, getRecommendation,\n'
                    'logActivity, getEffectiveness, getFeedbackLoopAnalytics',
            ha='center', va='center', fontsize=7.2, color='#2C3E50')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig12_frontend_architecture.png'), dpi=300)
    plt.close()
    print("Saved fig12_frontend_architecture.png")


if __name__ == '__main__':
    print("Generating CWIP Report Figures...")
    generate_fig1()
    generate_fig2()
    generate_fig3()
    generate_fig4()
    generate_fig5()
    generate_fig6()
    generate_fig7()
    generate_fig8()
    generate_fig9()
    generate_fig10()
    generate_fig11()
    generate_fig12()
    print("All 12 figures successfully generated!")
