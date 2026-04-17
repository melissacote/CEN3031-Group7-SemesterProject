# utils/pdf_generator.py
from xhtml2pdf import pisa
from jinja2 import Template
from datetime import datetime
from services.reports import get_medication_history, get_patient_dob, get_report_date_range
from services.medication import get_medications_for_management

def generate_pdf_report(user_id, patient_name, start_date=None, end_date=None, output_path="Patient_Report.pdf", report_type="Both (Medication List & Admin Record)"):
    # Determine what sections to show based on the report_type
    show_admin_record = "Administration Record" in report_type or "Both" in report_type
    show_med_list = "Medication List" in report_type or "Both" in report_type

    # Fetch the data
    # 1. Fetch Administration Logs
    log_data = []
    if show_admin_record:
        # Note: logs is already a list of dictionaries from our updated reports.py
        logs, final_start, final_end = get_medication_history(user_id, start_date, end_date)
        log_data = logs
    else:
        # Get default date range for the header if we skipped fetching logs
        final_start, final_end = get_report_date_range(start_date, end_date)

    # 2. Fetch Active Medication List
    active_meds = []
    if show_med_list:
        active_meds = get_medications_for_management(user_id)

    # Load the HTML template
    with open("templates/report_template.html", "r") as file:
        template_str = file.read()
        
    template = Template(template_str)
    
    # Inject the data into the HTML
    html_content = template.render(
        patient_name=patient_name,
        patient_dob=get_patient_dob(user_id),
        start_date=final_start,
        end_date=final_end,
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        report_type=report_type,
        show_admin_record=show_admin_record,
        show_med_list=show_med_list,
        log_data=log_data,
        active_meds=active_meds
    )
    
    # Generate the PDF using xhtml2pdf
    try:
        # pisa requires a file object opened in write-binary mode
        with open(output_path, "w+b") as result_file:
            # Create the PDF
            pisa_status = pisa.CreatePDF(html_content, dest=result_file)
            
        # pisa.CreatePDF returns an object with an 'err' flag
        if pisa_status.err:
            print("Error generating PDF with xhtml2pdf.")
            return False
            
        print(f"Report successfully generated at: {output_path}")
        return True
        
    except Exception as e:
        print(f"Exception during PDF generation: {e}")
        return False