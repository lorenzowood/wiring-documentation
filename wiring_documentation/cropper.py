import fitz  # PyMuPDF
import csv
import sys

def crop_pdf(input_pdf, output_pdf, crops_csv):
    # Open the original PDF
    doc = fitz.open(input_pdf)
    
    # Create a new PDF for output
    new_pdf = fitz.open()

    # Read the crop information from the CSV
    with open(crops_csv, newline='') as csvfile:
        crop_reader = csv.reader(csvfile)
        for row in crop_reader:
            # Extract the information from each row
            page_name, source_page_number, x1, y1, x2, y2 = row
            source_page_number = int(source_page_number)
            x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
            
            # Load the page
            page = doc.load_page(source_page_number - 1)  # Page numbers are 0-indexed in PyMuPDF

            # Define the crop rectangle (left, top, right, bottom)
            crop = fitz.Rect(x1, y1, x2, y2)
            
            # Set the crop rectangle for the page
            page.set_cropbox(crop)

            # Create a new page with the cropped content
            new_page = new_pdf.new_page(width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(new_page.rect, doc, source_page_number - 1)

    # Save the cropped pages to the output PDF
    new_pdf.save(output_pdf)

if __name__ == "__main__":
    # Command-line arguments: source PDF, target PDF, and CSV file
    if len(sys.argv) != 4:
        print("Usage: python cropper.py <input_pdf> <output_pdf> <crops_csv>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    crops_csv = sys.argv[3]

    # Call the function to process the PDFs
    crop_pdf(input_pdf, output_pdf, crops_csv)
    print(f"Cropped PDF saved to: {output_pdf}")
