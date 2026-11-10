"""
CWIP Academic Report Builder Module
Provides styling, XML manipulation, table formatting, figure insertion,
code block styling, and document structuring for python-docx.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Colors
COLOR_PRIMARY_HEX = "1B365D"       # Academic Navy
COLOR_SECONDARY_HEX = "2980B9"     # Cerulean
COLOR_DARK_SLATE_HEX = "2C3E50"    # Dark Slate
COLOR_LIGHT_BG_HEX = "F8F9FA"      # Very Light Gray
COLOR_BORDER_HEX = "BDC3C7"        # Muted Gray Border
COLOR_CALLOUT_BG_HEX = "EAEDED"    # Callout Box Background

COLOR_PRIMARY = RGBColor(27, 54, 93)
COLOR_SECONDARY = RGBColor(41, 128, 185)
COLOR_TEXT = RGBColor(44, 62, 80)
COLOR_MUTED = RGBColor(127, 140, 141)


class CWIPReportBuilder:
    def __init__(self):
        self.doc = docx.Document()
        self._setup_page_geometry()
        self._setup_styles()

    def _setup_page_geometry(self):
        """Standard university academic thesis margins."""
        section = self.doc.sections[0]
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    def _setup_styles(self):
        """Configure standard academic document styles."""
        styles = self.doc.styles

        # Normal (Body Text)
        normal = styles['Normal']
        normal.font.name = 'Times New Roman'
        normal.font.size = Pt(12)
        normal.font.color.rgb = COLOR_TEXT
        normal.paragraph_format.line_spacing = 1.5
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.space_before = Pt(0)
        normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_cover_page(self, logo_path):
        """Generate university standard cover page matching reference format."""
        p_title = self.doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_before = Pt(12)
        p_title.paragraph_format.space_after = Pt(18)
        run = p_title.add_run("MINOR PROJECT REPORT")
        run.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = COLOR_PRIMARY

        p_sub = self.doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sub.paragraph_format.space_after = Pt(28)
        run_proj = p_sub.add_run("Cognitive Workflow Intelligence Platform (CWIP)")
        run_proj.bold = True
        run_proj.italic = True
        run_proj.font.size = Pt(17)
        run_proj.font.color.rgb = COLOR_PRIMARY

        p_sub2 = self.doc.add_paragraph()
        p_sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sub2.paragraph_format.space_after = Pt(6)
        r = p_sub2.add_run("Submitted in partial fulfillment of the requirements\nfor the award of the degree of")
        r.italic = True
        r.font.size = Pt(12)

        p_deg = self.doc.add_paragraph()
        p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_deg.paragraph_format.space_after = Pt(28)
        r_deg1 = p_deg.add_run("Bachelor of Technology\n")
        r_deg1.bold = True
        r_deg1.font.size = Pt(14)
        r_deg2 = p_deg.add_run("Computer Science and Engineering\n(Data Science & Artificial Intelligence)")
        r_deg2.bold = True
        r_deg2.font.size = Pt(13)

        # Team & Supervisor Table (Two Column)
        t_meta = self.doc.add_table(rows=1, cols=2)
        t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_meta.autofit = False
        t_meta.columns[0].width = Inches(3.0)
        t_meta.columns[1].width = Inches(3.25)

        # Left cell: Supervisor
        c_sup = t_meta.cell(0, 0)
        p_s = c_sup.paragraphs[0]
        p_s.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_s.paragraph_format.line_spacing = 1.15
        r = p_s.add_run("Supervisor:\n")
        r.bold = True
        r.font.size = Pt(11)
        r = p_s.add_run("Ms. Namrata Sukhija\nAssistant Professor\nDept. of CSE")
        r.font.size = Pt(11)

        # Right cell: Students
        c_stu = t_meta.cell(0, 1)
        p_st = c_stu.paragraphs[0]
        p_st.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_st.paragraph_format.line_spacing = 1.15
        r = p_st.add_run("Submitted by:\n")
        r.bold = True
        r.font.size = Pt(11)
        students = [
            ("Arshnav Singhal", "11023210024"),
            ("Nikhil Kumar Singh", "11023210033"),
            ("Navvya Chaudhary", "11023210035")
        ]
        for name, regno in students:
            r = p_st.add_run(f"{name} ({regno})\n")
            r.font.size = Pt(11)

        # Logo
        if os.path.exists(logo_path):
            p_logo = self.doc.add_paragraph()
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_logo.paragraph_format.space_before = Pt(20)
            p_logo.paragraph_format.space_after = Pt(14)
            p_logo.add_run().add_picture(logo_path, width=Inches(2.2))

        # Institutional Footer Block
        p_inst = self.doc.add_paragraph()
        p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_inst.paragraph_format.line_spacing = 1.15
        p_inst.paragraph_format.space_before = Pt(8)
        p_inst.paragraph_format.space_after = Pt(0)
        
        r = p_inst.add_run("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING\n"
                           "FACULTY OF ENGINEERING AND TECHNOLOGY\n"
                           "SRM UNIVERSITY DELHI-NCR\n"
                           "39, RAJIV GANDHI EDUCATION CITY, SONEPAT, HARYANA – 131029\n"
                           "MAY 2026")
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = COLOR_PRIMARY

        self.doc.add_page_break()

    def add_approval_page(self):
        """Generate university Project Approval Page matching exact template."""
        p_dept = self.doc.add_paragraph()
        p_dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_dept.paragraph_format.space_before = Pt(10)
        p_dept.paragraph_format.space_after = Pt(4)
        r = p_dept.add_run("DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        p_app = self.doc.add_paragraph()
        p_app.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_app.paragraph_format.space_after = Pt(4)
        r = p_app.add_run("PROJECT APPROVAL PAGE")
        r.bold = True
        r.underline = True
        r.font.size = Pt(13)

        p_deg = self.doc.add_paragraph()
        p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_deg.paragraph_format.space_after = Pt(18)
        r = p_deg.add_run("B.Tech. CSE (Data Science & Artificial Intelligence)")
        r.bold = True
        r.font.size = Pt(12)

        # Group and Session line
        p_grp = self.doc.add_paragraph()
        p_grp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_grp.paragraph_format.space_after = Pt(16)
        r1 = p_grp.add_run("Group No: 21")
        r1.bold = True
        r1.font.size = Pt(11)
        r_sp = p_grp.add_run("\t\t\t\t\t\t")
        r2 = p_grp.add_run("Session: 2025 - 2026")
        r2.bold = True
        r2.font.size = Pt(11)

        # Student section
        p_sub = self.doc.add_paragraph()
        p_sub.paragraph_format.space_after = Pt(8)
        r = p_sub.add_run("To be filled in by the student: -")
        r.bold = True
        r.font.size = Pt(11)

        p_stinfo = self.doc.add_paragraph()
        p_stinfo.paragraph_format.line_spacing = 1.3
        p_stinfo.paragraph_format.space_after = Pt(14)
        r = p_stinfo.add_run("Student Name(s): Arshnav Singhal, Nikhil Kumar Singh, Navvya Chaudhary\n"
                             "Enrolment Number: 11023210024, 11023210033, 11023210035\n"
                             "Project Title: Cognitive Workflow Intelligence Platform (CWIP)\n\n"
                             "Signature: __________________________")
        r.font.size = Pt(11)

        # Supervisor section
        p_sup_sec = self.doc.add_paragraph()
        p_sup_sec.paragraph_format.space_before = Pt(10)
        p_sup_sec.paragraph_format.space_after = Pt(8)
        r = p_sup_sec.add_run("To be filled in by the supervisor: -")
        r.bold = True
        r.font.size = Pt(11)

        p_cert = self.doc.add_paragraph()
        p_cert.paragraph_format.line_spacing = 1.3
        p_cert.paragraph_format.space_after = Pt(20)
        r = p_cert.add_run("This is to certify that the project submitted and presented by the above-mentioned "
                           "student(s) is COMPLETE ACCEPTED and the draft of the graduation project report has "
                           "been corrected for all content flaws, typing errors, and language mistakes.")
        r.font.size = Pt(11)

        # Signatures table
        t_sigs = self.doc.add_table(rows=3, cols=2)
        t_sigs.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_sigs.columns[0].width = Inches(4.2)
        t_sigs.columns[1].width = Inches(2.0)

        sigs = [
            ("Supervisor name and Signature: Ms. Namrata Sukhija", "Date: ____________"),
            ("Examiner's Name and Signature: __________________", "Date: ____________"),
            ("HOD's Signature: Prof. M. Mohan", "Date: ____________")
        ]
        for idx, (s1, s2) in enumerate(sigs):
            row = t_sigs.rows[idx]
            p0 = row.cells[0].paragraphs[0]
            p0.paragraph_format.space_after = Pt(12)
            r0 = p0.add_run(s1)
            r0.font.size = Pt(10.5)

            p1 = row.cells[1].paragraphs[0]
            p1.paragraph_format.space_after = Pt(12)
            r1 = p1.add_run(s2)
            r1.font.size = Pt(10.5)

        p_dept_off = self.doc.add_paragraph()
        p_dept_off.paragraph_format.space_before = Pt(16)
        p_dept_off.paragraph_format.space_after = Pt(8)
        r = p_dept_off.add_run("For Departmental Office use only")
        r.bold = True
        r.font.size = Pt(11)

        p_dept_rec = self.doc.add_paragraph()
        p_dept_rec.paragraph_format.space_after = Pt(0)
        r = p_dept_rec.add_run("Date Received: ____________________\t\tSignatures: ____________________")
        r.font.size = Pt(10.5)

        self.doc.add_page_break()

    def add_declaration_page(self):
        """Generate Candidate's Declaration matching university format."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(20)
        r = p_head.add_run("CANDIDATE’S DECLARATION")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        p_body1 = self.doc.add_paragraph()
        p_body1.paragraph_format.line_spacing = 1.5
        p_body1.paragraph_format.space_after = Pt(14)
        r = p_body1.add_run("We hereby certify that the work which is being presented in the project entitled ")
        r.font.size = Pt(12)
        r_proj = p_body1.add_run("Cognitive Workflow Intelligence Platform (CWIP)")
        r_proj.bold = True
        r_proj.font.size = Pt(12)
        r2 = p_body1.add_run(" in partial fulfillment of the requirement for the award of the Degree of "
                             "Bachelor of Technology in Computer Science and Engineering [in specialization with "
                             "DS and AI] of SRM University, Delhi-NCR, Sonepat, Haryana, (India) is an authentic "
                             "record of our own work carried out under the supervision of ")
        r2.font.size = Pt(12)
        r_sup = p_body1.add_run("Ms. Namrata Sukhija")
        r_sup.bold = True
        r_sup.font.size = Pt(12)
        r3 = p_body1.add_run(", as a Minor Project in 6th Semester during the academic year 2025-26.")
        r3.font.size = Pt(12)

        p_body2 = self.doc.add_paragraph()
        p_body2.paragraph_format.line_spacing = 1.5
        p_body2.paragraph_format.space_after = Pt(36)
        r = p_body2.add_run("The matter presented in this project has not been submitted for the award of any other "
                            "degree of this or any other Institute/University.")
        r.font.size = Pt(12)

        # Candidates Signatures block
        candidates = [
            ("Arshnav Singhal", "11023210024"),
            ("Nikhil Kumar Singh", "11023210033"),
            ("Navvya Chaudhary", "11023210035")
        ]
        for name, regno in candidates:
            p_cand = self.doc.add_paragraph()
            p_cand.paragraph_format.line_spacing = 1.15
            p_cand.paragraph_format.space_after = Pt(14)
            r = p_cand.add_run(f"{name}\nRegistration No.: {regno}")
            r.font.size = Pt(11)

        self.doc.add_page_break()

    def add_certificate_page(self):
        """Generate university Certificate page."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(24)
        r = p_head.add_run("CERTIFICATE")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        p_body = self.doc.add_paragraph()
        p_body.paragraph_format.line_spacing = 1.5
        p_body.paragraph_format.space_after = Pt(36)
        r = p_body.add_run("This is to certify that the ")
        r.font.size = Pt(12)
        r_proj = p_body.add_run("Cognitive Workflow Intelligence Platform (CWIP)")
        r_proj.bold = True
        r_proj.font.size = Pt(12)
        r2 = p_body.add_run(" project is a Bonafide work completed as a Minor Project (Course Code: 23CS0304) "
                            "in partial fulfilment for the award of the degree of Bachelor of Technology in "
                            "CSE-DS & AI under the guidance of ")
        r2.font.size = Pt(12)
        r_sup = p_body.add_run("Ms. Namrata Sukhija")
        r_sup.bold = True
        r2_end = p_body.add_run(". This project is submitted by Arshnav Singhal (11023210024), "
                                "Nikhil Kumar Singh (11023210033), and Navvya Chaudhary (11023210035), "
                                "during the academic Semester VI of year 2025-2026 of SRM University, "
                                "Delhi-NCR, Sonipat, Haryana.")
        r2_end.font.size = Pt(12)

        # Faculty signatories table
        t_cert = self.doc.add_table(rows=2, cols=2)
        t_cert.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_cert.columns[0].width = Inches(3.2)
        t_cert.columns[1].width = Inches(3.0)

        c00 = t_cert.cell(0, 0).paragraphs[0]
        c00.paragraph_format.space_after = Pt(28)
        r = c00.add_run("Ms. Namrata Sukhija\nSupervisor\nAssistant Professor, Dept. of CSE")
        r.bold = True
        r.font.size = Pt(11)

        c01 = t_cert.cell(0, 1).paragraphs[0]
        c01.paragraph_format.space_after = Pt(28)
        r = c01.add_run("Dr. Mohd. Kaleem\nProject Coordinator\nDept. of CSE")
        r.bold = True
        r.font.size = Pt(11)

        c10 = t_cert.cell(1, 0).paragraphs[0]
        c10.paragraph_format.space_after = Pt(14)
        r = c10.add_run("Dr. Mohd Dilshad Ansari\nProgram Coordinator\nDept. of CSE")
        r.bold = True
        r.font.size = Pt(11)

        c11 = t_cert.cell(1, 1).paragraphs[0]
        c11.paragraph_format.space_after = Pt(14)
        r = c11.add_run("Prof. M. Mohan\nHead of Department (HOD)\nDept. of CSE")
        r.bold = True
        r.font.size = Pt(11)

        self.doc.add_page_break()

    def add_acknowledgement_page(self):
        """Generate university standard Acknowledgement page."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(20)
        r = p_head.add_run("ACKNOWLEDGEMENT")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        p1 = self.doc.add_paragraph()
        p1.paragraph_format.line_spacing = 1.5
        p1.paragraph_format.space_after = Pt(12)
        r = p1.add_run("Most importantly, we would like to express our immense gratitude to our supervisor ")
        r.font.size = Pt(12)
        r_sup = p1.add_run("Ms. Namrata Sukhija")
        r_sup.bold = True
        r_sup.font.size = Pt(12)
        r1_end = p1.add_run(" for her patient guidance, encouragement, intellectual rigor, and architectural advice "
                            "she has provided throughout this project. The knowledge and software engineering discipline "
                            "we have gained under her mentorship will stay with us for years to come. We have been "
                            "exceptionally fortunate to have a supervisor who demonstrated deep concern for technical "
                            "integrity, algorithmic correctness, and academic excellence, responding to our design "
                            "inquiries with prompt and constructive feedback. Her infectious enthusiasm and dedication "
                            "have been major driving forces throughout this endeavor.")
        r1_end.font.size = Pt(12)

        p2 = self.doc.add_paragraph()
        p2.paragraph_format.line_spacing = 1.5
        p2.paragraph_format.space_after = Pt(12)
        r = p2.add_run("We also sincerely thank our Project Coordinator, ")
        r.font.size = Pt(12)
        r_pc = p2.add_run("Dr. Mohd. Kaleem")
        r_pc.bold = True
        r_pc.font.size = Pt(12)
        r2_end = p2.add_run(", for his continuous logistical coordination, constructive milestone reviews, and "
                            "invaluable support throughout the lifecycle of the Minor Project.")
        r2_end.font.size = Pt(12)

        p3 = self.doc.add_paragraph()
        p3.paragraph_format.line_spacing = 1.5
        p3.paragraph_format.space_after = Pt(12)
        r = p3.add_run("We extend our sincere indebtedness to the ")
        r.font.size = Pt(12)
        r_pcm = p3.add_run("Project Committee Members")
        r_pcm.bold = True
        r_pcm.font.size = Pt(12)
        r3_end = p3.add_run(" of the Department of Computer Science and Engineering, SRM University Delhi-NCR, "
                            "as our architecture has benefited substantially from their incisive reviews, rigorous "
                            "critiques, and valuable feedback during progress examinations.")
        r3_end.font.size = Pt(12)

        p4 = self.doc.add_paragraph()
        p4.paragraph_format.line_spacing = 1.5
        p4.paragraph_format.space_after = Pt(12)
        r = p4.add_run("We also warmly thank our Program Coordinator, ")
        r.font.size = Pt(12)
        r_prog = p4.add_run("Dr. Mohd Dilshad Ansari")
        r_prog.bold = True
        r_prog.font.size = Pt(12)
        r4_end = p4.add_run(", for his visionary academic leadership and steadfast support across the curriculum.")
        r4_end.font.size = Pt(12)

        p5 = self.doc.add_paragraph()
        p5.paragraph_format.line_spacing = 1.5
        p5.paragraph_format.space_after = Pt(12)
        r = p5.add_run("We feel profoundly compelled to articulate our deepest thankfulness to ")
        r.font.size = Pt(12)
        r_hod = p5.add_run("Prof. M. Mohan")
        r_hod.bold = True
        r_hod.font.size = Pt(12)
        r5_end = p5.add_run(", Head of Department of Computer Science and Engineering, SRM University, whose constant "
                            "encouragement and academic vision provide a thriving environment for advanced technical research.")
        r5_end.font.size = Pt(12)

        p6 = self.doc.add_paragraph()
        p6.paragraph_format.line_spacing = 1.5
        p6.paragraph_format.space_after = Pt(24)
        r = p6.add_run("Lastly, we express our heartfelt thanks to all teaching and non-teaching staff members, lab "
                       "instructors, and our peers for their unwavering cooperation and assistance throughout our academic journey.")
        r.font.size = Pt(12)

        self.doc.add_page_break()

    def add_abstract_page(self):
        """Generate comprehensive Abstract and Keywords pages."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(18)
        r = p_head.add_run("ABSTRACT")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        p1 = self.doc.add_paragraph()
        p1.paragraph_format.line_spacing = 1.5
        p1.paragraph_format.space_after = Pt(12)
        r = p1.add_run(
            "The Cognitive Workflow Intelligence Platform (CWIP) is an adaptive learning intelligence platform "
            "engineered to address one of the most critical deficiencies in contemporary educational technology: "
            "the inability of conventional assessment systems to differentiate between diagnostic failure detection "
            "and causal root-cause remediation. Standard learning management systems and competitive assessment platforms "
            "habitually track coarse, topic-level aggregate accuracy percentages and generate indiscriminate, high-friction "
            "recommendations (e.g., advising a student failing complex binary search problems merely to 'practice more binary search'). "
            "Such superficial feedback fails to discover whether the underlying impediment stems from an unmastered prerequisite "
            "(such as array boundary condition reasoning), procedural slip, or cognitive fatigue. Consequently, learners endure "
            "substantial cognitive overload, wasted effort, and premature stagnation."
        )
        r.font.size = Pt(12)

        p2 = self.doc.add_paragraph()
        p2.paragraph_format.line_spacing = 1.5
        p2.paragraph_format.space_after = Pt(12)
        r = p2.add_run(
            "CWIP introduces a mathematically disciplined, multi-tier architectural framework that fuses directed graph theory, "
            "supervised machine learning, psychometric knowledge tracing, and enterprise-grade transactional concurrency control. "
            "The foundational domain structure is formulated as a Directed Acyclic Graph (DAG) using NetworkX, where nodes signify "
            "granular cognitive skills and directed edges strictly encode prerequisite dependencies (Prerequisite → Dependent). "
            "A deterministic multi-hop bottleneck scoring algorithm traverses the transitive dependency tree, isolating the precise "
            "root-cause prerequisite responsible for multi-hop failure propagation."
        )
        r.font.size = Pt(12)

        p3 = self.doc.add_paragraph()
        p3.paragraph_format.line_spacing = 1.5
        p3.paragraph_format.space_after = Pt(12)
        r = p3.add_run(
            "To operationalize the pedagogical Minimum Intervention Principle (MIP), CWIP models instructional intervention through "
            "six distinct canonical actions: practice_current, practice_prerequisite, review_concept, easy_practice, hard_practice, "
            "and take_assessment. A 100-estimator Scikit-learn Random Forest classifier ingests a 10-dimensional engineered feature "
            "vector (capturing historical accuracy, exponential decay velocity, difficulty stratification, trial-and-error ratios, "
            "and behavioral consistency) to select the optimal canonical action. Crucially, CWIP maintains rigorous scientific "
            "governance: the current Random Forest model is explicitly demarcated as a synthetic development model that imitates "
            "expert heuristic policy, while genuine educational effectiveness is evaluated strictly through real learner data."
        )
        r.font.size = Pt(12)

        p4 = self.doc.add_paragraph()
        p4.paragraph_format.line_spacing = 1.5
        p4.paragraph_format.space_after = Pt(12)
        r = p4.add_run(
            "The system architecture is implemented using FastAPI in Python 3.14 on the backend and React 19 with Vite on the frontend, "
            "persisted across a normalized PostgreSQL relational database. Transactional integrity is guaranteed during concurrent "
            "activity logging via PostgreSQL row-level locking (SELECT ... FOR UPDATE), preventing race conditions in atomic mastery "
            "recalculation and outcome attribution. Furthermore, CWIP establishes an automated Step 4 Statistical Evaluation Readiness "
            "governance module that enforces 12-category exclusion filtering, dual-track cross-validation (Track A: Disjoint Learner Clusters; "
            "Track B: Chronological Split with zero future leakage), and deterministic data sufficiency gates (N >= 30, N >= 150, K >= 15). "
            "The entire platform is verified against an exhaustive suite of 176 automated pytest unit, integration, security, and "
            "concurrency tests, establishing a robust, production-ready foundation for AI-guided personalized education."
        )
        r.font.size = Pt(12)

        p_kw = self.doc.add_paragraph()
        p_kw.paragraph_format.line_spacing = 1.5
        p_kw.paragraph_format.space_before = Pt(16)
        p_kw.paragraph_format.space_after = Pt(0)
        r_kwh = p_kw.add_run("Keywords: ")
        r_kwh.bold = True
        r_kwh.font.size = Pt(12)
        r_kwt = p_kw.add_run(
            "Adaptive Learning, Skill Gap Intelligence, Directed Acyclic Graph, Minimum Intervention Principle, "
            "Knowledge Tracing, Random Forest, FastAPI, React 19, PostgreSQL Row-Level Locking, Explainable AI in Education (XAI-Edu)."
        )
        r_kwt.italic = True
        r_kwt.font.size = Pt(12)

        self.doc.add_page_break()

    def add_table_of_contents_placeholder(self, toc_items):
        """Generate structured Table of Contents."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(18)
        r = p_head.add_run("Table of Contents")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        t_toc = self.doc.add_table(rows=0, cols=2)
        t_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_toc.columns[0].width = Inches(5.5)
        t_toc.columns[1].width = Inches(0.8)

        for title, page, is_bold in toc_items:
            row = t_toc.add_row()
            p0 = row.cells[0].paragraphs[0]
            p0.paragraph_format.line_spacing = 1.15
            p0.paragraph_format.space_after = Pt(2)
            r0 = p0.add_run(title)
            r0.font.size = Pt(10.5)
            r0.bold = is_bold
            if is_bold:
                r0.font.color.rgb = COLOR_PRIMARY

            p1 = row.cells[1].paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p1.paragraph_format.line_spacing = 1.15
            p1.paragraph_format.space_after = Pt(2)
            r1 = p1.add_run(str(page))
            r1.font.size = Pt(10.5)
            r1.bold = is_bold

        self.doc.add_page_break()

    def add_list_of_tables_placeholder(self, tables_list):
        """Generate List of Tables."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(18)
        r = p_head.add_run("LIST OF TABLES")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        t_lot = self.doc.add_table(rows=0, cols=2)
        t_lot.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_lot.columns[0].width = Inches(5.5)
        t_lot.columns[1].width = Inches(0.8)

        for t_label, page in tables_list:
            row = t_lot.add_row()
            p0 = row.cells[0].paragraphs[0]
            p0.paragraph_format.line_spacing = 1.2
            p0.paragraph_format.space_after = Pt(3)
            r0 = p0.add_run(t_label)
            r0.font.size = Pt(10)

            p1 = row.cells[1].paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p1.paragraph_format.line_spacing = 1.2
            p1.paragraph_format.space_after = Pt(3)
            r1 = p1.add_run(str(page))
            r1.font.size = Pt(10)

        self.doc.add_page_break()

    def add_list_of_figures_placeholder(self, figures_list):
        """Generate List of Figures."""
        p_head = self.doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_before = Pt(12)
        p_head.paragraph_format.space_after = Pt(18)
        r = p_head.add_run("LIST OF FIGURES")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = COLOR_PRIMARY

        t_lof = self.doc.add_table(rows=0, cols=2)
        t_lof.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_lof.columns[0].width = Inches(5.5)
        t_lof.columns[1].width = Inches(0.8)

        for f_label, page in figures_list:
            row = t_lof.add_row()
            p0 = row.cells[0].paragraphs[0]
            p0.paragraph_format.line_spacing = 1.2
            p0.paragraph_format.space_after = Pt(3)
            r0 = p0.add_run(f_label)
            r0.font.size = Pt(10)

            p1 = row.cells[1].paragraphs[0]
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p1.paragraph_format.line_spacing = 1.2
            p1.paragraph_format.space_after = Pt(3)
            r1 = p1.add_run(str(page))
            r1.font.size = Pt(10)

        self.doc.add_page_break()

    def add_chapter_heading(self, chapter_title):
        """Add formal chapter title."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(14)
        run = p.add_run(chapter_title)
        run.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = COLOR_PRIMARY

    def add_heading_1(self, heading_text):
        """Add level-1 section heading."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(heading_text)
        run.bold = True
        run.font.size = Pt(13.5)
        run.font.color.rgb = COLOR_PRIMARY

    def add_heading_2(self, heading_text):
        """Add level-2 subsection heading."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(heading_text)
        run.bold = True
        run.font.size = Pt(12.5)
        run.font.color.rgb = RGBColor(44, 62, 80)

    def add_heading_3(self, heading_text):
        """Add level-3 subsection heading."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(heading_text)
        run.bold = True
        run.italic = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(52, 73, 94)

    def add_body_paragraph(self, text):
        """Add standard justified 1.5-spaced body paragraph."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(text)
        r.font.size = Pt(12)
        return p

    def add_bullet_point(self, bold_prefix, text):
        """Add formal bullet list item."""
        p = self.doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.4
        p.paragraph_format.space_after = Pt(4)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix + ": ")
            r_pre.bold = True
            r_pre.font.size = Pt(12)
        r = p.add_run(text)
        r.font.size = Pt(12)
        return p

    def add_figure(self, fig_path, caption_text, width_inches=6.0):
        """Embed centered figure with standard caption."""
        if os.path.exists(fig_path):
            p_img = self.doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(10)
            p_img.paragraph_format.space_after = Pt(4)
            p_img.add_run().add_picture(fig_path, width=Inches(width_inches))

            p_cap = self.doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(12)
            r = p_cap.add_run(caption_text)
            r.italic = True
            r.bold = True
            r.font.size = Pt(10.5)
            r.font.color.rgb = COLOR_TEXT

    def add_styled_table(self, caption_text, headers, rows_data, col_widths=None):
        """Add styled academic table with dark header, alternating rows, and border."""
        p_cap = self.doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_cap.paragraph_format.space_before = Pt(12)
        p_cap.paragraph_format.space_after = Pt(4)
        r = p_cap.add_run(caption_text)
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = COLOR_PRIMARY

        table = self.doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        # Header Row
        hdr_cells = table.rows[0].cells
        for idx, text in enumerate(headers):
            hdr_cells[idx].text = text
            # Format header cell
            p = hdr_cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.0
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)
            # Background shading
            hdr_cells[idx]._tc.get_or_add_tcPr().append(
                parse_xml(f'<w:shd {nsdecls("w")} w:fill="{COLOR_PRIMARY_HEX}"/>')
            )

        # Data Rows
        for r_idx, row_values in enumerate(rows_data):
            row_cells = table.rows[r_idx + 1].cells
            bg_fill = COLOR_LIGHT_BG_HEX if (r_idx % 2 == 1) else "FFFFFF"
            for c_idx, val in enumerate(row_values):
                row_cells[c_idx].text = str(val)
                p = row_cells[c_idx].paragraphs[0]
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.15
                if c_idx == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(9.5)
                # Background
                row_cells[c_idx]._tc.get_or_add_tcPr().append(
                    parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_fill}"/>')
                )

        # Set Column Widths
        if col_widths:
            for i, col in enumerate(table.columns):
                w = Inches(col_widths[i])
                for cell in col.cells:
                    cell.width = w

        p_after = self.doc.add_paragraph()
        p_after.paragraph_format.space_after = Pt(6)

    def add_code_block(self, code_text):
        """Add highlighted code block in styled single-cell table."""
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.25)
        cell._tc.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="{COLOR_LIGHT_BG_HEX}"/>')
        )
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.line_spacing = 1.1
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(code_text)
        r.font.name = 'Consolas'
        r.font.size = Pt(9.0)
        r.font.color.rgb = RGBColor(33, 47, 61)

        p_after = self.doc.add_paragraph()
        p_after.paragraph_format.space_after = Pt(6)

    def add_callout_box(self, title, text):
        """Add formal alert / note callout box with border."""
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.25)
        cell._tc.get_or_add_tcPr().append(
            parse_xml(f'<w:shd {nsdecls("w")} w:fill="{COLOR_CALLOUT_BG_HEX}"/>')
        )
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r_t = p.add_run(f"[{title}] ")
        r_t.bold = True
        r_t.font.size = Pt(10.5)
        r_t.font.color.rgb = COLOR_PRIMARY
        r = p.add_run(text)
        r.font.size = Pt(10.5)

        p_after = self.doc.add_paragraph()
        p_after.paragraph_format.space_after = Pt(6)

    def save(self, filepath):
        """Save the docx package to disk."""
        self.doc.save(filepath)
        print(f"Report saved successfully to {filepath}")
