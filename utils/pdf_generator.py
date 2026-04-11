# services/pdf_generator.py
from xhtml2pdf import pisa
from jinja2 import Template
from datetime import datetime
from services.reports import get_medication_history, get_patient_dob

def generate_pdf_report(user_id, patient_name, start_date=None, end_date=None, output_path="Patient_Report.pdf"):
    # Fetch the data
    logs, final_start, final_end = get_medication_history(user_id, start_date, end_date)
    
    # Format the data into a dictionary for the template
    log_data = [{"medication_name": r[0], "dosage": r[1], "date_taken": r[2], "time_taken": r[3]} for r in logs]

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
        log_data=log_data
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