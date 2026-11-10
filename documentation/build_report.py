"""
CWIP Minor Project Report Master Assembly Script
Compiles all preliminaries, chapters, tables, figures, code blocks, and references
into C:\\Users\\DELL\\Desktop\\CWIP\\documentation\\CWIP_Minor_Project_Report.docx.
"""

import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from report_builder import CWIPReportBuilder
from chapters_1_to_3 import build_chapters_1_to_3
from chapters_4_to_5 import build_chapters_4_and_5
from chapters_6_to_10 import build_chapters_6_to_10

DOCS_DIR = os.path.abspath('documentation')
FIGURES_DIR = os.path.join(DOCS_DIR, 'figures')
OUTPUT_PATH = os.path.join(DOCS_DIR, 'CWIP_Minor_Project_Report.docx')
LOGO_PATH = os.path.join(FIGURES_DIR, 'extracted_logo_0.png')


def add_page_number_to_run(run):
    """Inserts Word dynamic PAGE field into a text run."""
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)


def assemble_cwip_report():
    print("=" * 70)
    print("STARTING CWIP MINOR PROJECT REPORT COMPILATION")
    print("=" * 70)

    builder = CWIPReportBuilder()

    # 1. Preliminaries
    print("Compiling Cover Page...")
    builder.add_cover_page(LOGO_PATH)

    print("Compiling Project Approval Page...")
    builder.add_approval_page()

    print("Compiling Candidate's Declaration...")
    builder.add_declaration_page()

    print("Compiling Certificate...")
    builder.add_certificate_page()

    print("Compiling Acknowledgement...")
    builder.add_acknowledgement_page()

    print("Compiling Abstract & Keywords...")
    builder.add_abstract_page()

    # Table of Contents Items
    toc_data = [
        ("CANDIDATE’S DECLARATION", "iii", True),
        ("CERTIFICATE", "iv", True),
        ("ACKNOWLEDGEMENT", "v", True),
        ("ABSTRACT", "vi", True),
        ("LIST OF TABLES", "viii", True),
        ("LIST OF FIGURES", "ix", True),
        ("CHAPTER-1: INTRODUCTION", "1", True),
        ("  1.1 Background and Context", "1", False),
        ("  1.2 Problem Statement", "3", False),
        ("  1.3 Motivation and Educational Significance", "5", False),
        ("  1.4 Project Vision and Architectural Objectives", "7", False),
        ("  1.5 Scope and Operational Boundaries", "8", False),
        ("CHAPTER-2: LITERATURE REVIEW", "10", True),
        ("  2.1 Evolution of Learning Analytics and Knowledge Tracing", "10", False),
        ("  2.2 Deep Knowledge Tracing and Modern Sequence Models", "13", False),
        ("  2.3 Cognitive Diagnosis Models and Q-Matrix Formulation", "16", False),
        ("  2.4 Educational Graph Modeling and Prerequisite Discovery", "18", False),
        ("  2.5 Behavioral Signal Processing in Learner Modeling", "19", False),
        ("  2.6 Comparative Analysis of Contemporary Systems", "21", False),
        ("  2.7 Identified Research Gaps Addressed by CWIP", "23", False),
        ("CHAPTER-3: METHODOLOGY AND SYSTEM DESIGN", "24", True),
        ("  3.1 High-Level Architecture Overview", "24", False),
        ("  3.2 Data Acquisition and Ingestion Pipeline", "27", False),
        ("  3.3 Mathematical Formulation of Feature Engineering Pipeline", "29", False),
        ("  3.4 Skill Dependency Graph Formulation", "33", False),
        ("  3.5 Bottleneck Scoring and Multi-Hop Diagnosis Algorithm", "36", False),
        ("  3.6 Machine Learning Model Design and Governance", "38", False),
        ("  3.7 Recommendation Policy and Six Canonical Actions", "39", False),
        ("  3.8 Statistical Evaluation Readiness Governance (Step 4)", "40", False),
        ("  3.9 System Modeling and Design Diagrams", "43", False),
        ("  3.10 Database Schema Design and Normalization", "49", False),
        ("  3.11 RESTful API Interface Specification", "50", False),
        ("CHAPTER-4: ARCHITECTURE AND IMPLEMENTATION DETAILS", "52", True),
        ("  4.1 Backend Architecture and FastAPI Service Layer", "52", False),
        ("  4.2 Concurrency Control and Row-Level Locking", "54", False),
        ("  4.3 Skill Graph Module Implementation", "56", False),
        ("  4.4 Real-World Learning Data Collection and Feedback Loop", "58", False),
        ("  4.5 Machine Learning Pipeline and Development Model", "60", False),
        ("  4.6 Evaluation Readiness and Governance Engine", "61", False),
        ("  4.7 Frontend Dashboard Implementation", "62", False),
        ("  4.8 Comprehensive Production Code Walkthroughs", "64", False),
        ("CHAPTER-5: RESULTS, SYSTEM VERIFICATION AND TESTING", "70", True),
        ("  5.1 Test Automation Architecture and 176 Pytest Baseline", "70", False),
        ("  5.2 Multi-User Isolation and Security Boundary Verification", "73", False),
        ("  5.3 Concurrency and Transactional Integrity Verification", "74", False),
        ("  5.4 System Latency and Performance Benchmarks", "76", False),
        ("  5.5 Development ML Model Evaluation and Policy Imitation", "77", False),
        ("  5.6 Baseline Model Comparative Analysis", "79", False),
        ("  5.7 Step 4 Data Readiness Audit and Funnel Results", "81", False),
        ("  5.8 Observational Learning Effectiveness Analytics", "83", False),
        ("  5.9 Frontend Verification and Production Build Audit", "84", False),
        ("CHAPTER-6: LIMITATIONS AND OPERATIONAL CONSTRAINTS", "86", True),
        ("  6.1 Data Scarcity and Cold-Start Realities", "86", False),
        ("  6.2 Synthetic Model Policy Demarcation", "87", False),
        ("  6.3 Self-Reported Adherence Vulnerabilities", "88", False),
        ("  6.4 Static Graph Topology vs Dynamic Prerequisite Discovery", "89", False),
        ("  6.5 Architectural and Environmental Boundaries", "90", False),
        ("CHAPTER-7: FUTURE WORK AND STRATEGIC ROADMAP", "92", True),
        ("  7.1 Transition to Empirical Model Deployment (Step 6)", "92", False),
        ("  7.2 Continuous Online Retraining and Automated Re-Calibration", "93", False),
        ("  7.3 AST-Based Code Analysis and Keystroke Dynamics", "94", False),
        ("  7.4 Automated Graph Structure Discovery", "95", False),
        ("  7.5 External LMS Integration and Standardized Interoperability", "96", False),
        ("  7.6 Longitudinal Randomized Controlled Trials (RCT)", "97", False),
        ("CHAPTER-8: CONCLUSION", "98", True),
        ("  8.1 Summary of Contributions", "98", False),
        ("  8.2 Academic and Industry Significance", "99", False),
        ("  8.3 Concluding Remarks", "100", False),
        ("CHAPTER-9: APPENDICES", "101", True),
        ("  Appendix-A: Installation, Environment Configuration & Guide", "101", False),
        ("  Appendix-B: Complete REST API Endpoint Specification", "103", False),
        ("  Appendix-C: Complete Database Data Dictionary", "105", False),
        ("  Appendix-D: Mathematical Formalism & Feature Extraction", "107", False),
        ("  Appendix-E: Project Timeline & Development Gantt Chart", "109", False),
        ("CHAPTER-10: REFERENCES", "110", True)
    ]

    print("Compiling Table of Contents...")
    builder.add_table_of_contents_placeholder(toc_data)

    # List of Tables
    tables_data = [
        ("Table 2.1: Comparative Analysis of Adaptive Learning Platforms", "21"),
        ("Table 3.1: CWIP Activity Telemetry Ingestion Schema", "28"),
        ("Table 3.2: Complete Summary of 10-Dimensional Engineered Features", "33"),
        ("Table 3.3: Step 4 Statistical Evaluation Readiness Governance Gates", "42"),
        ("Table 3.4: PostgreSQL Relational Database Schema & Constraints", "49"),
        ("Table 3.5: CWIP RESTful API Endpoint Specifications", "51"),
        ("Table 5.1: Exhaustive Automated Test Suite Verification (176 Tests)", "71"),
        ("Table 5.2: CWIP Subsystem Latency and Throughput Benchmarks", "76"),
        ("Table 5.3: Synthetic Development Model Classification Performance", "78"),
        ("Table 5.4: Baseline Model Formulations and Benchmark Performance", "80"),
        ("Table 5.5: Step 4 Evaluation Readiness Gate Audit Results", "82"),
        ("Table 9.1: Workstation Hardware & System Software Specifications", "101"),
        ("Table 9.2: Comprehensive CWIP REST API Endpoint Specifications", "103"),
        ("Table 9.3: CWIP Complete PostgreSQL Database Data Dictionary", "105"),
        ("Table 9.4: Mathematical Notation and Formulation Reference", "107"),
        ("Table 9.5: Project Development Schedule and Milestone Allocation", "109")
    ]

    print("Compiling List of Tables...")
    builder.add_list_of_tables_placeholder(tables_data)

    # List of Figures
    figures_data = [
        ("Figure 1 — CWIP Multi-Tier System Architecture Overview", "26"),
        ("Figure 2 — Real-World Learning Data Collection & Feedback Loop Architecture", "58"),
        ("Figure 3 — Skill Dependency Directed Acyclic Graph (NetworkX DAG Model)", "34"),
        ("Figure 4 — Level-0 Context Data Flow Diagram (DFD)", "44"),
        ("Figure 5 — Level-1 DFD Decomposition", "45"),
        ("Figure 6 — UML Use Case Diagram", "46"),
        ("Figure 7 — UML Class Diagram (Domain Models & Service Layer)", "47"),
        ("Figure 8 — UML Sequence Diagram (Recommendation Generation & Feedback)", "48"),
        ("Figure 9 — Relational Database Entity-Relationship (ER) Diagram", "49"),
        ("Figure 10 — ML Pipeline & Dual-Track Partitioning Strategy", "41"),
        ("Figure 11 — Statistical Evaluation Readiness Gates & Sufficiency Funnel", "42"),
        ("Figure 12 — React 19 Frontend Dashboard Component Hierarchy & UI State", "62")
    ]

    print("Compiling List of Figures...")
    builder.add_list_of_figures_placeholder(figures_data)

    # 2. Chapters 1 to 3
    print("Compiling Chapters 1 to 3...")
    build_chapters_1_to_3(builder, FIGURES_DIR)

    # 3. Chapters 4 and 5
    print("Compiling Chapters 4 and 5...")
    build_chapters_4_and_5(builder, FIGURES_DIR)

    # 4. Chapters 6 to 10
    print("Compiling Chapters 6 to 10...")
    build_chapters_6_to_10(builder)

    # 5. Header and Footer Configuration
    print("Configuring dynamic header and page numbering footer...")
    for s_idx, section in enumerate(builder.doc.sections):
        # Header
        header = section.header
        p_hdr = header.paragraphs[0]
        p_hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_hdr.paragraph_format.space_after = Pt(2)
        r_hdr = p_hdr.add_run("Cognitive Workflow Intelligence Platform (CWIP) | Minor Project Report")
        r_hdr.font.name = "Times New Roman"
        r_hdr.font.size = Pt(8.5)
        r_hdr.font.color.rgb = RGBColor(127, 140, 141)

        # Footer
        footer = section.footer
        p_ftr = footer.paragraphs[0]
        p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_ftr = p_ftr.add_run()
        add_page_number_to_run(r_ftr)
        r_ftr.font.name = "Times New Roman"
        r_ftr.font.size = Pt(10)

    # 6. Save Document
    print(f"Saving finalized document to {OUTPUT_PATH}...")
    builder.save(OUTPUT_PATH)

    # 7. Quality & Metrics Inspection
    print("=" * 70)
    print("COMPILATION COMPLETE! INSPECTING DOCUMENT METRICS...")
    doc_saved = docx.Document(OUTPUT_PATH)
    total_paras = len(doc_saved.paragraphs)
    total_tables = len(doc_saved.tables)
    total_words = sum(len(p.text.split()) for p in doc_saved.paragraphs)
    for t in doc_saved.tables:
        for r in t.rows:
            for c in r.cells:
                total_words += sum(len(p.text.split()) for p in c.paragraphs)

    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"Output File: {OUTPUT_PATH}")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Total Paragraphs: {total_paras}")
    print(f"Total Styled Tables: {total_tables}")
    print(f"Total Word Count: {total_words:,} words")
    print(f"Estimated Formatted Page Count: ~{round(total_words / 270) + total_tables + 12} pages (Target: 100-110+ pages)")
    print("=" * 70)


if __name__ == '__main__':
    assemble_cwip_report()
