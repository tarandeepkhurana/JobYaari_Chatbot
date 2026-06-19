import pdfplumber
import logging
import asyncio

logger = logging.getLogger("resume.resume_reader")


async def extract_text_from_pdf(
    file_path,
) -> str:

    try:
        logger.info(f"Resume text extraction started: {file_path}")

        text_chunks = []

        with pdfplumber.open(file_path) as pdf:

            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    text_chunks.append(page_text)
        
        logger.info(f"Resume text extraction completed: {file_path}")
        
        return "\n".join(text_chunks)

    except Exception:
        logger.exception("PDF text extraction failed")
        return ""
    
async def main():
    text = await extract_text_from_pdf(
        "src/sample_resumes/Tarandeep_Resume.pdf"
    )

    print(text[:500])


if __name__ == "__main__":
    asyncio.run(main())