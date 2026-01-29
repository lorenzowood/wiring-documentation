import sys
import weasyprint


def html_to_pdf(input_filename, output_filename):
    """Convert HTML file to PDF."""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"HTML file not found: {input_filename}")

    weasyprint.HTML(string=html_content).write_pdf(output_filename)


def main():
    # Ensure input and output filenames are provided
    if len(sys.argv) != 3:
        print("Usage: python make_pdf.py <input_filename> <output_filename>")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    try:
        html_to_pdf(input_filename, output_filename)
        print(f"PDF saved to {output_filename}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
