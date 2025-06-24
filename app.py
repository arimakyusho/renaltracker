import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date
from PIL import Image
import os
import pandas as pd
from fpdf import FPDF
import base64

# ======================
# APP CONFIGURATION
# ======================
st.set_page_config(
    page_title="Renal Tracker Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main styles */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Sidebar styles */
    [data-testid="stSidebar"] {
        background-color: #e3f2fd !important;
    }
    
    /* Button styles */
    .stButton>button {
        border: 1px solid #0d6efd;
        border-radius: 8px;
        padding: 8px 16px;
        background-color: #0d6efd;
        color: white;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #0b5ed7;
        border-color: #0a58ca;
    }
    
    /* Secondary button */
    .stButton>button[kind="secondary"] {
        background-color: #6c757d;
        border-color: #6c757d;
    }
    
    /* Input styles */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea,
    .stDateInput>div>div>input,
    .stSelectbox>div>div>select {
        border-radius: 8px;
        padding: 8px 12px;
    }
    
    /* Card styles */
    .patient-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Table styles */
    .stDataFrame {
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Metric cards */
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Logo styling */
    .logo-container {
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ======================
# SESSION STATE
# ======================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_type" not in st.session_state:
    st.session_state.user_type = ""
if "full_name" not in st.session_state:
    st.session_state.full_name = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "editing_patient" not in st.session_state:
    st.session_state.editing_patient = None
if "viewing_patient" not in st.session_state:
    st.session_state.viewing_patient = None
if "editing_med" not in st.session_state:
    st.session_state.editing_med = None
if "editing_diag" not in st.session_state:
    st.session_state.editing_diag = None
if "adding_med_for" not in st.session_state:
    st.session_state.adding_med_for = None
if "adding_diag_for" not in st.session_state:
    st.session_state.adding_diag_for = None
if "editing_profile" not in st.session_state:
    st.session_state.editing_profile = False
if "generating_report_for" not in st.session_state:
    if "adding_lab_for" not in st.session_state:
        st.session_state.adding_lab_for = None
    st.session_state.generating_report_for = None

# ======================
# HELPER FUNCTIONS
# ======================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_age(birth_date):
    if not birth_date:
        return 0
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_db_connection():
    return sqlite3.connect("renal_tracker.db")

def create_placeholder_logo():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (300, 100), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Renal Tracker Pro", fill=(255,255,0))
    return img

def load_logo():
    try:
        logo_path = "renal_tracker_logo.png"
        if os.path.exists(logo_path):
            return Image.open(logo_path)
        else:
            st.warning("Logo file not found. Using placeholder.")
            return create_placeholder_logo()
    except Exception as e:
        st.error(f"Failed to load logo: {e}")
        return create_placeholder_logo()

def generate_patient_report(patient_id):
    try:
        with get_db_connection() as conn:
            # Get patient data
            patient = conn.execute(
                "SELECT * FROM patients WHERE id = ?", 
                (patient_id,)
            ).fetchone()
            
            if not patient:
                st.error("Patient not found")
                return None

            # Get medications (latest first)
            medications = conn.execute(
                """SELECT medication_name, dosage, frequency, 
                   start_date, end_date, notes 
                   FROM medications 
                   WHERE patient_id = ? 
                   ORDER BY start_date DESC""", 
                (patient_id,)
            ).fetchall()
            
            # Get diagnostics (latest first)
            diagnostics = conn.execute(
                """SELECT test_name, test_date, results, notes 
                   FROM diagnostics 
                   WHERE patient_id = ? 
                   ORDER BY test_date DESC""", 
                (patient_id,)
            ).fetchall()
        
        # Create PDF with proper margins
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Add logo
        try:
            pdf.image("renal_tracker_logo.png", x=10, y=8, w=40)
        except:
            pass
        
        # Set initial position below logo
        pdf.set_y(40)
        
        # Report header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Patient Monthly Medical Report", 0, 1, 'C')
        pdf.ln(10)
        
        # Report date
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'R')
        pdf.ln(10)
        
        # Patient Information Section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Patient Information", 0, 1, 'L')
        pdf.set_font("Arial", '', 12)
        
        # Calculate age if birthday exists
        age = ""
        if patient[2]:
            birth_date = datetime.strptime(patient[2], "%Y-%m-%d").date()
            age = f" ({calculate_age(birth_date)} years)"
        
        # Patient info rows
        info_data = [
            ["Full Name", patient[1]],
            ["Date of Birth", f"{patient[2]}{age}" if patient[2] else "Not specified"],
            ["Primary Diagnosis", patient[8] if patient[8] else "Not specified"]
        ]
        
        for label, value in info_data:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(50, 8, label + ":", 0, 0, 'L')
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 8, str(value), 0, 'L')
            pdf.ln(2)
        
        pdf.ln(10)
        
        # Current Medications Section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Current Medications", 0, 1, 'L')
        pdf.ln(5)
        
        if medications:
            # Table header
            col_widths = [60, 30, 30, 30, 30]
            pdf.set_font("Arial", 'B', 10)
            for i, header in enumerate(["Medication", "Dosage", "Frequency", "Start Date", "End Date"]):
                pdf.cell(col_widths[i], 8, header, 1, 0, 'C')
            pdf.ln()
            
            # Table content
            pdf.set_font("Arial", '', 10)
            for med in medications:
                for i, value in enumerate(med[:5]):  # First 5 fields
                    cell_value = str(value) if value is not None else ""
                    if i == 4 and not cell_value:  # End Date
                        cell_value = "Ongoing"
                    pdf.cell(col_widths[i], 8, cell_value, 1, 0, 'L')
                pdf.ln()
                
                # Add notes if available
                if med[5]:  # Notes field
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(sum(col_widths), 6, f"Notes: {med[5]}", 0, 1, 'L')
                    pdf.set_font("Arial", '', 10)
        else:
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 8, "No medications recorded", 0, 1, 'L')
        
        pdf.ln(15)
               # Lab Results Section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Laboratory Values", 0, 1, 'L')
        pdf.ln(5)

        with get_db_connection() as conn:
            labs = conn.execute(
                "SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC",
                (patient_id,)
            ).fetchall()
            columns = [col[1] for col in conn.execute("PRAGMA table_info(lab_results)")]

        if labs:
            for lab in labs:
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, f"Test Date: {lab[2]}", 0, 1)
                pdf.set_font("Arial", '', 11)
                labels = columns[3:]  # skip id, patient_id, test_date
                for i, label in enumerate(labels, start=3):
                    if lab[i]:
                        pdf.cell(60, 8, f"{label.replace('_', ' ').title()}: ", 0, 0)
                        pdf.cell(0, 8, str(lab[i]), 0, 1)
                pdf.ln(5)
        else:
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 8, "No laboratory results recorded", 0, 1, 'L')

        pdf.ln(10)

        if diagnostics:
            # Table header
            col_widths = [70, 30, 0]  # Last column takes remaining space
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_widths[0], 8, "Test Name", 1, 0, 'C')
            pdf.cell(col_widths[1], 8, "Test Date", 1, 0, 'C')
            pdf.cell(col_widths[2], 8, "Results", 1, 1, 'C')
            
            # Table content
            pdf.set_font("Arial", '', 10)
            for diag in diagnostics:
                pdf.cell(col_widths[0], 8, diag[0], 1, 0, 'L')  # Test Name
                pdf.cell(col_widths[1], 8, diag[1], 1, 0, 'L')  # Test Date
                pdf.multi_cell(col_widths[2], 8, diag[2] if diag[2] else "No results", 1, 'L')  # Results
                
                # Add notes if available
                if diag[3]:  # Notes field
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(20, 6, "Notes:", 0, 0, 'L')
                    pdf.multi_cell(0, 6, diag[3], 0, 'L')
                    pdf.set_font("Arial", '', 10)
        else:
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 8, "No diagnostic tests recorded", 0, 1, 'L')
        
 
        # Footer with user information (centered)
        pdf.set_font("Arial", 'I', 8)
        footer_text = f"Generated by: {st.session_state.full_name} ({st.session_state.username}) | Renal Tracker Pro"
        page_width = pdf.w - 2 * pdf.l_margin
        pdf.set_x((pdf.w - pdf.get_string_width(footer_text)) / 2)
        pdf.cell(pdf.get_string_width(footer_text), 10, footer_text)
        
        # Return PDF bytes
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin1')
        return bytes(pdf_output)
        
    except Exception as e:
        st.error(f"Failed to generate report: {str(e)}")
        return None

def create_download_button(pdf_bytes, patient_name):
    # Generate a filename
    filename = f"Renal_Report_{patient_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    # Create download button
    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary"
    )

logo = load_logo()

# ======================
# MEDICATION & DIAGNOSTIC FORMS
# ======================
def add_medication_form():
    st.header("💊 Add New Medication")
    
    with st.form("add_med_form"):
        medication_name = st.text_input("Medication Name*")
        dosage = st.text_input("Dosage*")
        frequency = st.text_input("Frequency*")
        start_date = st.date_input("Start Date*", value=date.today())
        end_date = st.date_input("End Date (optional)", value=None)
        notes = st.text_area("Notes")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Medication", type="primary"):
                if not medication_name or not dosage or not frequency:
                    st.error("Please fill all required fields (*)")
                else:
                    with get_db_connection() as conn:
                        conn.execute(
                            """INSERT INTO medications 
                            (patient_id, medication_name, dosage, frequency, 
                            start_date, end_date, notes) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                st.session_state.adding_med_for,
                                medication_name,
                                dosage,
                                frequency,
                                str(start_date),
                                str(end_date) if end_date else None,
                                notes
                            )
                        )
                        conn.commit()
                    st.success("Medication added successfully!")
                    st.session_state.adding_med_for = None
                    st.rerun()
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.session_state.adding_med_for = None
                st.rerun()

def edit_medication_form():
    with get_db_connection() as conn:
        med = conn.execute(
            "SELECT * FROM medications WHERE id = ?",
            (st.session_state.editing_med,)
        ).fetchone()
    
    st.header("✏️ Edit Medication")
    
    with st.form("edit_med_form"):
        medication_name = st.text_input("Medication Name*", value=med[2])
        dosage = st.text_input("Dosage*", value=med[3])
        frequency = st.text_input("Frequency*", value=med[4])
        start_date = st.date_input("Start Date*", 
                                 value=datetime.strptime(med[5], "%Y-%m-%d").date())
        end_date = st.date_input("End Date", 
                               value=datetime.strptime(med[6], "%Y-%m-%d").date() if med[6] else None)
        notes = st.text_area("Notes", value=med[7] if med[7] else "")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Changes", type="primary"):
                if not medication_name or not dosage or not frequency:
                    st.error("Please fill all required fields (*)")
                else:
                    with get_db_connection() as conn:
                        conn.execute(
                            """UPDATE medications SET
                            medication_name = ?,
                            dosage = ?,
                            frequency = ?,
                            start_date = ?,
                            end_date = ?,
                            notes = ?
                            WHERE id = ?""",
                            (
                                medication_name,
                                dosage,
                                frequency,
                                str(start_date),
                                str(end_date) if end_date else None,
                                notes,
                                st.session_state.editing_med
                            )
                        )
                        conn.commit()
                    st.success("Medication updated successfully!")
                    st.session_state.editing_med = None
                    st.rerun()
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.session_state.editing_med = None
                st.rerun()

def add_diagnostic_form():
    st.header("🩺 Add New Diagnostic Test")
    
    with st.form("add_diag_form"):
        test_name = st.text_input("Test Name*")
        test_date = st.date_input("Test Date*", value=date.today())
        results = st.text_area("Results")
        notes = st.text_area("Notes")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Diagnostic", type="primary"):
                if not test_name:
                    st.error("Test name is required!")
                else:
                    with get_db_connection() as conn:
                        conn.execute(
                            """INSERT INTO diagnostics 
                            (patient_id, test_name, test_date, results, notes) 
                            VALUES (?, ?, ?, ?, ?)""",
                            (
                                st.session_state.adding_diag_for,
                                test_name,
                                str(test_date),
                                results,
                                notes
                            )
                        )
                        conn.commit()
                    st.success("Diagnostic test added successfully!")
                    st.session_state.adding_diag_for = None
                    st.rerun()
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.session_state.adding_diag_for = None
                st.rerun()

def edit_diagnostic_form():
    with get_db_connection() as conn:
        diag = conn.execute(
            "SELECT * FROM diagnostics WHERE id = ?",
            (st.session_state.editing_diag,)
        ).fetchone()
    
    st.header("✏️ Edit Diagnostic Test")
    
    with st.form("edit_diag_form"):
        test_name = st.text_input("Test Name*", value=diag[2])
        test_date = st.date_input("Test Date*", 
                                value=datetime.strptime(diag[3], "%Y-%m-%d").date())
        results = st.text_area("Results", value=diag[4] if diag[4] else "")
        notes = st.text_area("Notes", value=diag[5] if diag[5] else "")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Changes", type="primary"):
                if not test_name:
                    st.error("Test name is required!")
                else:
                    with get_db_connection() as conn:
                        conn.execute(
                            """UPDATE diagnostics SET
                            test_name = ?,
                            test_date = ?,
                            results = ?,
                            notes = ?
                            WHERE id = ?""",
                            (
                                test_name,
                                str(test_date),
                                results,
                                notes,
                                st.session_state.editing_diag
                            )
                        )
                        conn.commit()
                    st.success("Diagnostic test updated successfully!")
                    st.session_state.editing_diag = None
                    st.rerun()
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.session_state.editing_diag = None
                st.rerun()

# ======================
# DATABASE INITIALIZATION
# ======================
def init_db():
    conn = sqlite3.connect("renal_tracker.db")
    c = conn.cursor()
    
    # Check if users table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_table_exists = c.fetchone()
    
    if not users_table_exists:
        c.execute('''
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                user_type TEXT NOT NULL CHECK(user_type IN ('Admin', 'Doctor', 'Staff')),
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # Add missing columns if they don't exist
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'full_name' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''")
        if 'user_type' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN user_type TEXT NOT NULL DEFAULT 'Staff'")
        if 'status' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        if 'created_at' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Create patients table
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            birthday TEXT,
            sex TEXT,
            age INTEGER,
            address TEXT,
            contact_no TEXT,
            emergency_contact TEXT,
            diagnosis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (created_by) REFERENCES users(username)
        )
    ''')
    
    # Create medications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            medication_name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')
    
    # Create diagnostics table
    c.execute('''
        CREATE TABLE IF NOT EXISTS diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            test_name TEXT NOT NULL,
            test_date TEXT NOT NULL,
            results TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    ''')
    
    # Create lab_results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS lab_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            test_date TEXT NOT NULL,
            rbc TEXT, hematocrit TEXT, hemoglobin TEXT, wbc TEXT, platelet_count TEXT,
            neutrophils TEXT, lymphocytes TEXT, monocytes TEXT, basophils TEXT, eosinophils TEXT,
            mcv TEXT, mch TEXT, mchc TEXT, sodium TEXT, potassium TEXT, creatinine TEXT,
            calcium TEXT, phosphorus TEXT, urea_nitrogen TEXT, albumin TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)
    
    # Create default admin if none exists
    c.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, full_name, user_type) VALUES (?, ?, ?, ?)",
            ("admin", hash_password("admin123"), "System Administrator", "Admin")
        )
    conn.commit()
    conn.close()

# ======================
# AUTHENTICATION
# ======================
def show_login():
    st.empty()
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(logo, width=250)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if "reset_password" in st.query_params:
            with st.form("password_reset_form"):
                st.subheader("🔒 Password Reset")
                username = st.text_input("Username")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("Reset Password"):
                    if new_password != confirm_password:
                        st.error("Passwords don't match!")
                    else:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET password = ? WHERE username = ?",
                                (hash_password(new_password), username)
                            )
                            conn.commit()
                        st.success("Password updated!")
                        st.query_params.clear()
                        st.rerun()
            return
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", type="primary"):
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT username, password, user_type, full_name, status FROM users WHERE username = ?",
                            (username,)
                        )
                        user = cursor.fetchone()
                    
                    if user and hash_password(password) == user[1]:
                        if user[4] != "active":
                            st.error(f"Account is {user[4]}!")
                        else:
                            st.session_state.authenticated = True
                            st.session_state.username = user[0]
                            st.session_state.user_type = user[2]
                            st.session_state.full_name = user[3]
                            st.session_state.current_page = "Home"
                            st.rerun()
                    else:
                        st.error("Invalid username or password")
                except sqlite3.OperationalError as e:
                    st.error("Database error. Please contact administrator.")
                    st.stop()
        
        st.markdown(
            "<div style='text-align: center;'>"
            "<a href='?reset_password=true' style='color: gray;'>Forgot password?</a>"
            "</div>",
            unsafe_allow_html=True
        )

# ======================
# PROFILE MANAGEMENT
# ======================
def show_profile_button():
    col1, col2 = st.columns([5,1])
    with col2:
        if st.button(f"👤 {st.session_state.full_name}", key="profile_button"):
            st.session_state.current_page = "Profile"
            st.rerun()

def manage_profile():
    st.header("My Profile")
    
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT username, full_name FROM users WHERE username = ?",
            (st.session_state.username,)
        ).fetchone()
    
    if st.session_state.editing_profile:
        with st.form("profile_form"):
            st.subheader("Edit Profile")
            
            new_full_name = st.text_input("Full Name", value=user[1])
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save Changes", type="primary"):
                    update_fields = {}
                    if new_full_name != user[1]:
                        update_fields['full_name'] = new_full_name
                    if new_password and new_password == confirm_password:
                        update_fields['password'] = hash_password(new_password)
                    elif new_password:
                        st.error("Passwords don't match!")
                        return
                    
                    if update_fields:
                        with get_db_connection() as conn:
                            if 'password' in update_fields:
                                conn.execute(
                                    "UPDATE users SET full_name = ?, password = ? WHERE username = ?",
                                    (new_full_name, update_fields['password'], st.session_state.username)
                                )
                            else:
                                conn.execute(
                                    "UPDATE users SET full_name = ? WHERE username = ?",
                                    (new_full_name, st.session_state.username)
                                )
                            conn.commit()
                        st.session_state.full_name = new_full_name
                        st.success("Profile updated successfully!")
                        st.session_state.editing_profile = False
                        st.rerun()
                    else:
                        st.warning("No changes made")
            with col2:
                if st.form_submit_button("Cancel", type="secondary"):
                    st.session_state.editing_profile = False
                    st.rerun()
    else:
        st.write(f"**Username:** {user[0]}")
        st.write(f"**Full Name:** {user[1]}")
        st.write(f"**Account Type:** {st.session_state.user_type}")
        
        if st.button("Edit Profile", type="primary"):
            st.session_state.editing_profile = True
            st.rerun()
        
        if st.button("Back to Home", type="secondary"):
            st.session_state.current_page = "Home"
            st.rerun()

# ======================
# HOME PAGE
# ======================
def show_home():
    show_profile_button()
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(logo, width=300)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align: center;'>Welcome, {st.session_state.full_name}!</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size: 18px;'>You are logged in as {st.session_state.user_type}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Metrics
    with get_db_connection() as conn:
        patient_count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        active_patients = conn.execute(
            "SELECT COUNT(DISTINCT patient_id) FROM medications WHERE end_date IS NULL OR end_date >= date('now')"
        ).fetchone()[0]
        recent_patients = conn.execute(
            "SELECT COUNT(*) FROM patients WHERE created_at >= date('now', '-30 days')"
        ).fetchone()[0]
    
    st.subheader("Practice Overview", divider="blue")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Total Patients</h3>
            <h1 style="color: #0d6efd;">{patient_count}</h1>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>Active Patients</h3>
            <h1 style="color: #0d6efd;">{active_patients}</h1>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>New Patients (30d)</h3>
            <h1 style="color: #0d6efd;">{recent_patients}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("Quick Actions", divider="blue")
    cols = st.columns(3)
    with cols[0]:
        if st.button("👥 View Patients", use_container_width=True, type="primary"):
            st.session_state.current_page = "Patient Management"
            st.rerun()
    with cols[1]:
        if st.session_state.user_type == "Admin" and st.button("👤 Manage Users", use_container_width=True, type="primary"):
            st.session_state.current_page = "User Management"
            st.rerun()
    with cols[2]:
        if st.button("📊 View Reports", use_container_width=True, type="primary"):
            st.session_state.current_page = "Reports"
            st.rerun()
    
    st.markdown("---")
    
    # Recent Activity
    st.subheader("Recent Activity", divider="blue")
    with get_db_connection() as conn:
        recent_patients = conn.execute(
            """SELECT p.id, p.full_name, p.diagnosis, u.full_name as created_by 
               FROM patients p JOIN users u ON p.created_by = u.username
               ORDER BY p.created_at DESC LIMIT 5"""
        ).fetchall()
    
    if recent_patients:
        for patient in recent_patients:
            with st.container():
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 8px; background-color: white; margin-bottom: 10px;">
                    <strong>{patient[1]}</strong> (ID: {patient[0]})<br>
                    <small>Diagnosis: {patient[2] or 'Not specified'} | Added by: {patient[3]}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No recent patient activity")

# ======================
# PATIENT MANAGEMENT
# ======================
def show_patient_details(patient_id):
    with get_db_connection() as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?",
            (patient_id,)
        ).fetchone()
        
        if not patient:
            st.error("Patient not found")
            return
    
    # Use tabs for better organization
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Medications", "Diagnostics", "Lab Values"])
    
    with tab1:  # Overview tab
        st.markdown(f"""
        <div class="patient-card">
            <h2>{patient[1]}</h2>
            <div style="display: flex; gap: 20px; margin-bottom: 20px;">
                <div style="flex: 1;">
                    <h4>📅 Personal Information</h4>
                    <p><strong>Birthday:</strong> {patient[2] or 'Not specified'}</p>
                    <p><strong>Sex:</strong> {patient[3] or 'Not specified'}</p>
                    <p><strong>Age:</strong> {patient[4] or 'Not specified'}</p>
                </div>
                <div style="flex: 1;">
                    <h4>🏠 Address</h4>
                    <p>{patient[5] or 'Not specified'}</p>
                    <h4>📞 Contact Information</h4>
                    <p><strong>Phone:</strong> {patient[6] or 'Not specified'}</p>
                    <p><strong>Emergency Contact:</strong> {patient[7] or 'Not specified'}</p>
                </div>
            </div>
            <h4>🩺 Diagnosis</h4>
            <p>{patient[8] or 'Not specified'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with tab2:  # Medications tab
        st.subheader("💊 Medications")
        with get_db_connection() as conn:
            medications = conn.execute(
                "SELECT * FROM medications WHERE patient_id = ? ORDER BY start_date DESC",
                (patient_id,)
            ).fetchall()
        
        if medications:
            med_df = pd.DataFrame(medications, columns=[
                "ID", "Patient ID", "Medication", "Dosage", "Frequency", 
                "Start Date", "End Date", "Notes"
            ])
            st.dataframe(
                med_df.drop(columns=["ID", "Patient ID"]), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No medications recorded for this patient")
        
        if st.session_state.user_type in ["Admin", "Staff"]:
            if st.button("➕ Add Medication", type="primary"):
                st.session_state.adding_med_for = patient_id
                st.rerun()
    
    with tab3:  # Diagnostics tab
        st.subheader("🩺 Diagnostics")
        with get_db_connection() as conn:
            diagnostics = conn.execute(
                "SELECT * FROM diagnostics WHERE patient_id = ? ORDER BY test_date DESC",
                (patient_id,)
            ).fetchall()
        
        if diagnostics:
            diag_df = pd.DataFrame(diagnostics, columns=[
                "ID", "Patient ID", "Test Name", "Test Date", "Results", "Notes"
            ])
            st.dataframe(
                diag_df.drop(columns=["ID", "Patient ID"]), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No diagnostics recorded for this patient")
        
        if st.session_state.user_type in ["Admin", "Staff"]:
            if st.button("➕ Add Diagnostic", type="primary"):
                st.session_state.adding_diag_for = patient_id
                st.rerun()
    
    
    with tab4:
        st.subheader("🧪 Lab Values")
        with get_db_connection() as conn:
            labs = conn.execute(
                "SELECT * FROM lab_results WHERE patient_id = ? ORDER BY test_date DESC",
                (patient_id,)
            ).fetchall()
            columns = [col[1] for col in conn.execute("PRAGMA table_info(lab_results)")]
        if labs:
            lab_df = pd.DataFrame(labs, columns=columns)
            st.dataframe(lab_df.drop(columns=["id", "patient_id"]), use_container_width=True)
        else:
            st.info("No lab values recorded for this patient.")

        if st.session_state.user_type in ["Admin", "Staff"]:
            if st.button("➕ Add Lab Values", type="primary"):
                st.session_state.adding_lab_for = patient_id
                st.rerun()

    # Generate Report Button
    if st.button("📄 Generate Patient Report", type="primary"):
        st.session_state.generating_report_for = patient_id
        st.rerun()
    
    if st.button("⬅️ Back to Patient List", type="secondary"):
        st.session_state.viewing_patient = None
        st.rerun()

def patient_management():
    show_profile_button()
    
    # Header and Add button in same section
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header("Patient Management")
    with col2:
        if st.session_state.user_type in ["Admin", "Staff"]:
            if st.button("➕ Add New Patient", type="primary", use_container_width=True):
                st.session_state.editing_patient = "new"
                st.rerun()
    
    # Search bar below
    search_term = st.text_input("🔍 Search patients by name or diagnosis", key="patient_search")
    # Add/Edit Patient Form
    if st.session_state.editing_patient:
        with st.form("patient_form", clear_on_submit=True):
            if st.session_state.editing_patient == "new":
                st.subheader("Add New Patient")
            else:
                st.subheader("Edit Patient")
                with get_db_connection() as conn:
                    patient = conn.execute(
                        "SELECT * FROM patients WHERE id = ?",
                        (st.session_state.editing_patient,)
                    ).fetchone()
            
            cols = st.columns(2)
            with cols[0]:
                full_name = st.text_input("Full Name*", value=patient[1] if st.session_state.editing_patient != "new" else "")
                birthday = st.date_input(
                    "Date of Birth*",
                    value=datetime.strptime(patient[2], "%Y-%m-%d").date() if st.session_state.editing_patient != "new" and patient[2] else date.today(),
                    min_value=date(1900, 1, 1),
                    max_value=date.today()
                )
                sex = st.selectbox(
                    "Sex",
                    ["Male", "Female", "Other"],
                    index=["Male", "Female", "Other"].index(patient[3]) if st.session_state.editing_patient != "new" and patient[3] else 0
                )
            with cols[1]:
                address = st.text_area("Address", value=patient[5] if st.session_state.editing_patient != "new" else "")
                contact_no = st.text_input("Contact Number", value=patient[6] if st.session_state.editing_patient != "new" else "")
                emergency_contact = st.text_input("Emergency Contact", value=patient[7] if st.session_state.editing_patient != "new" else "")
            
            diagnosis = st.text_input("Diagnosis", value=patient[8] if st.session_state.editing_patient != "new" else "")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save Patient", type="primary"):
                    if not full_name:
                        st.error("Full name is required!")
                    else:
                        age = calculate_age(birthday)
                        with get_db_connection() as conn:
                            if st.session_state.editing_patient == "new":
                                conn.execute(
                                    """
                                    INSERT INTO patients (
                                        full_name, birthday, sex, age, address,
                                        contact_no, emergency_contact, diagnosis, created_by
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (full_name, str(birthday), sex, age, address,
                                    contact_no, emergency_contact, diagnosis, st.session_state.username)
                                )
                            else:
                                conn.execute(
                                    """
                                    UPDATE patients SET
                                        full_name = ?, birthday = ?, sex = ?, age = ?,
                                        address = ?, contact_no = ?, emergency_contact = ?, diagnosis = ?
                                    WHERE id = ?
                                    """,
                                    (full_name, str(birthday), sex, age, address,
                                    contact_no, emergency_contact, diagnosis, st.session_state.editing_patient)
                                )
                            conn.commit()
                        st.session_state.editing_patient = None
                        st.rerun()
            with col2:
                if st.form_submit_button("Cancel", type="secondary"):
                    st.session_state.editing_patient = None
                    st.rerun()
    
    # Patient List with View Buttons
    with get_db_connection() as conn:
        patients = conn.execute(
            "SELECT * FROM patients WHERE full_name LIKE ? OR diagnosis LIKE ? ORDER BY full_name",
            (f"%{search_term}%", f"%{search_term}%")
        ).fetchall()
    
    if not patients:
        st.info("No patients found matching your search")
    else:
        for patient in patients:
            cols = st.columns([4, 1, 1])
            with cols[0]:
                st.write(f"**{patient[1]}** (ID: {patient[0]}) - {patient[8] if patient[8] else 'No diagnosis'}")
            with cols[1]:
                if st.button("👁️ View", key=f"view_{patient[0]}"):
                    st.session_state.viewing_patient = patient[0]
                    st.rerun()
            with cols[2]:
                if st.session_state.user_type in ["Admin", "Staff"]:
                    if st.button("✏️ Edit", key=f"edit_{patient[0]}"):
                        st.session_state.editing_patient = patient[0]
                        st.rerun()
            st.markdown("---")
    
    # Patient Details View
    if st.session_state.viewing_patient:
        show_patient_details(st.session_state.viewing_patient)

# ======================
# REPORTS
# ======================
def show_reports():
    show_profile_button()
    st.header("Patient Reports")
    
    # Search patients
    search_term = st.text_input("🔍 Search patients by name", key="report_search")
    
    with get_db_connection() as conn:
        patients = conn.execute(
            "SELECT id, full_name FROM patients WHERE full_name LIKE ? ORDER BY full_name",
            (f"%{search_term}%",)
        ).fetchall()
    
    if not patients:
        st.info("No patients found matching your search")
    else:
        selected_patient = st.selectbox(
            "Select a patient to generate report:",
            options=[f"{p[0]} - {p[1]}" for p in patients],
            index=0
        )
        
        patient_id = int(selected_patient.split(" - ")[0])
        patient_name = selected_patient.split(" - ")[1]
        
        if st.button("Generate PDF Report", type="primary"):
            with st.spinner("Generating report..."):
                try:
                    pdf_bytes = generate_patient_report(patient_id)
                    create_download_button(pdf_bytes, patient_name)
                except Exception as e:
                    st.error(f"Failed to generate report: {e}")

# ======================
# USER MANAGEMENT
# ======================
def manage_users():
    show_profile_button()
    st.header("User Management")
    
    # Only allow Admin to add new users
    if st.session_state.user_type == "Admin":
        with st.form("add_user_form"):
            st.subheader("Add New User")
            
            cols = st.columns(2)
            with cols[0]:
                new_username = st.text_input("Username*")
                new_password = st.text_input("Password*", type="password")
                full_name = st.text_input("Full Name*")
            with cols[1]:
                user_type = st.selectbox("Account Type*", ["Admin", "Doctor", "Staff"])
                status = st.selectbox("Status", ["active", "inactive"], index=0)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Create User", type="primary"):
                    if not new_username or not new_password or not full_name:
                        st.error("Please fill all required fields (*)")
                    else:
                        try:
                            with get_db_connection() as conn:
                                conn.execute(
                                    "INSERT INTO users (username, password, full_name, user_type, status) VALUES (?, ?, ?, ?, ?)",
                                    (new_username, hash_password(new_password), full_name, user_type, status)
                                )
                                conn.commit()
                            st.success(f"User {new_username} created successfully!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already exists!")
            with col2:
                if st.form_submit_button("Cancel", type="secondary"):
                    pass  # Just refreshes the form
    
    st.markdown("---")
    st.subheader("User Accounts")
    
    # User List with Actions
    with get_db_connection() as conn:
        users = conn.execute(
            "SELECT username, full_name, user_type, status FROM users ORDER BY username"
        ).fetchall()
    
    if not users:
        st.info("No user accounts found")
    else:
        for user in users:
            with st.container():
                cols = st.columns([3, 2, 1, 1, 1])
                with cols[0]:
                    st.write(f"**{user[0]}**")
                with cols[1]:
                    st.write(user[1])
                with cols[2]:
                    st.write(user[2])
                with cols[3]:
                    st.write(user[3].capitalize())
                with cols[4]:
                    if user[0] == st.session_state.username:
                        st.warning("Current user")
                    elif st.session_state.user_type == "Admin":
                        if st.button("Delete", key=f"delete_{user[0]}"):
                            with get_db_connection() as conn:
                                conn.execute(
                                    "DELETE FROM users WHERE username = ?",
                                    (user[0],)
                                )
                                conn.commit()
                            st.success(f"User {user[0]} deleted")
                            st.rerun()
            st.markdown("---")


def add_lab_values_form():
    st.header("🧪 Add Laboratory Values")
    with st.form("add_lab_form"):
        test_date = st.date_input("Test Date", value=date.today())
        RBC = st.text_input("RBC")
        hematocrit = st.text_input("Hematocrit")
        hemoglobin = st.text_input("Hemoglobin")
        WBC = st.text_input("WBC")
        platelet_count = st.text_input("Platelet Count")
        neutrophils = st.text_input("Neutrophils")
        lymphocytes = st.text_input("Lymphocytes")
        monocytes = st.text_input("Monocytes")
        basophils = st.text_input("Basophils")
        eosinophils = st.text_input("Eosinophils")
        mcv = st.text_input("MCV")
        mch = st.text_input("MCH")
        mchc = st.text_input("MCHC")
        sodium = st.text_input("Sodium")
        potassium = st.text_input("Potassium")
        creatinine = st.text_input("Creatinine")
        calcium = st.text_input("Calcium")
        phosphorus = st.text_input("Phosphorus")
        urea_nitrogen = st.text_input("Urea Nitrogen")
        albumin = st.text_input("Albumin (optional)")

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Lab Values", type="primary"):
                with get_db_connection() as conn:
                    conn.execute("""
                        INSERT INTO lab_results (
                            patient_id, test_date, rbc, hematocrit, hemoglobin, wbc, platelet_count,
                            neutrophils, lymphocytes, monocytes, basophils, eosinophils, mcv, mch, mchc,
                            sodium, potassium, creatinine, calcium, phosphorus, urea_nitrogen, albumin
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        st.session_state.adding_lab_for, str(test_date), rbc, hematocrit, hemoglobin, wbc,
                        platelet_count, neutrophils, lymphocytes, monocytes, basophils, eosinophils, mcv,
                        mch, mchc, sodium, potassium, creatinine, calcium, phosphorus, urea_nitrogen, albumin
                    ))
                    conn.commit()
                st.success("Lab values added successfully!")
                st.session_state.adding_lab_for = None
                st.rerun()
        with col2:
            if st.form_submit_button("Cancel", type="secondary"):
                st.session_state.adding_lab_for = None
                st.rerun()


# ======================
# MAIN APP
# ======================
def main():
    init_db()
    
    if not st.session_state.authenticated:
        show_login()
        return
    
    # Sidebar Navigation with active page highlighting
    with st.sidebar:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(logo, width=150)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Define navigation items
        nav_items = [
            {"label": "🏠 Home", "page": "Home"},
            {"label": "👥 Patients", "page": "Patient Management"},
            {"label": "📊 Reports", "page": "Reports"}
        ]
        
        # Add Admin items if applicable
        if st.session_state.user_type == "Admin":
            nav_items.insert(2, {"label": "👤 Users", "page": "User Management"})
        
        # Render navigation items
        for item in nav_items:
            if st.session_state.current_page == item["page"]:
                st.button(item["label"], 
                         use_container_width=True,
                         disabled=True,
                         help=f"Current page: {item['page']}")
            else:
                if st.button(item["label"], 
                           use_container_width=True,
                           help=f"Go to {item['page']}"):
                    st.session_state.current_page = item["page"]
                    st.rerun()
        
        st.markdown("---")
        if st.button("🚪 Logout", type="primary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.user_type = ""
            st.session_state.full_name = ""
            st.rerun()
    
    # Page Routing
    if st.session_state.editing_med:
        edit_medication_form()
    elif st.session_state.editing_diag:
        edit_diagnostic_form()
    elif st.session_state.adding_med_for:
        add_medication_form()
    elif st.session_state.adding_lab_for:
        add_lab_values_form()
    elif st.session_state.adding_diag_for:
        add_diagnostic_form()
    elif st.session_state.generating_report_for:
        pdf_bytes = generate_patient_report(st.session_state.generating_report_for)
        with get_db_connection() as conn:
            patient_name = conn.execute(
                "SELECT full_name FROM patients WHERE id = ?",
                (st.session_state.generating_report_for,)
            ).fetchone()[0]
        create_download_button(pdf_bytes, patient_name)
        st.session_state.generating_report_for = None
    elif st.session_state.current_page == "Home":
        show_home()
    elif st.session_state.current_page == "Patient Management":
        patient_management()
    elif st.session_state.current_page == "User Management":
        manage_users()
    elif st.session_state.current_page == "Profile":
        manage_profile()
    elif st.session_state.current_page == "Reports":
        show_reports()

if __name__ == "__main__":
    main()