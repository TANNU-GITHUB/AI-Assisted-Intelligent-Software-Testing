# Upload demo

Use these files to try the Live Lab upload controls:

- `checkout_demo.py`: upload in the Source Code panel.
- `checkout_requirements.pdf`: select **Upload PDF requirements** in the Requirements panel, then choose the file.
- `checkout_requirements.docx`: select **Upload requirements document** in the Requirements panel, then choose the file.
- `checkout_flowchart.png`: select **Upload flowchart image**, then choose the image.

The PDF, Word document, and diagram describe the same checkout behavior. Upload a
PDF or Word document to extract requirements, or upload the diagram to add its
extracted requirements to the text already in the editor. Then select
**Type or paste text** if you want to edit the requirements before running the
analysis. Click **Run Analysis** to generate test cases from the extracted
requirements and uploaded Python source.

Flowchart extraction uses the configured vision model when available and falls
back to the application's heuristic behavior when a vision model cannot be used.
