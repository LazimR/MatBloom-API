from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from app.api.services.answer_sheet_layout import build_answer_sheet_layout
from app.core.exceptions import OperationError, ValidationError


def _ensure_pdf_fonts_registered():
    try:
        pdfmetrics.getFont("Arial")
    except KeyError:
        pdfmetrics.registerFont(TTFont("Arial", "app/api/dependencies/ARIAL.TTF"))
        pdfmetrics.registerFont(TTFont("Arial-Bold", "app/api/dependencies/ARIALBD.TTF"))


def pdf_test_generate(test_name: str, questions: list, student_name: str, student_id: str = None):
    """
    Gera um PDF com a prova para o aluno e um gabarito separado
    
    Args:
        out_path: Caminho para salvar o PDF
        test_name: Nome da prova
        questions: Lista de dicionários com as questões
        student_name: Nome do aluno
        student_id: ID do aluno
    """
    if not test_name.strip():
        raise ValidationError("O nome da prova não pode estar vazio para gerar o PDF.")
    if not student_name.strip():
        raise ValidationError("O nome do aluno não pode estar vazio para gerar o PDF.")
    if not questions:
        raise ValidationError("A prova precisa ter pelo menos uma questão para gerar o PDF.")

    for index, question in enumerate(questions, start=1):
        if not question.get("enunciation"):
            raise ValidationError(f"A questão {index} está sem enunciado.")
        if not question.get("itens"):
            raise ValidationError(f"A questão {index} não possui alternativas.")

    _ensure_pdf_fonts_registered()
    buffer = BytesIO()

    try:
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        styles.add(ParagraphStyle(
            name="QuestionTitle",
            parent=styles["Normal"],
            fontName="Arial-Bold",
            fontSize=12,
            spaceAfter=6
        ))

        styles.add(ParagraphStyle(
            name="QuestionText",
            parent=styles["Normal"],
            fontName="Arial",
            fontSize=11,
            leading=14,
            spaceAfter=12
        ))

        styles.add(ParagraphStyle(
            name="ItemText",
            parent=styles["Normal"],
            fontName="Arial",
            fontSize=11,
            leftIndent=12,
            spaceAfter=6
        ))

        story = []
        student_identifier = student_id if student_id is not None else "-"

        story.append(Paragraph(test_name, styles["Title"]))
        story.append(Paragraph(f"Aluno: {student_name}  ID: {student_identifier}", styles["QuestionTitle"]))
        story.append(Spacer(1, 0.5 * inch))

        for i, question in enumerate(questions, 1):
            story.append(Paragraph(f"Questão {i}", styles["QuestionTitle"]))
            story.append(Paragraph(question["enunciation"], styles["QuestionText"]))

            for j, item in enumerate(question["itens"], 1):
                story.append(Paragraph(f"{chr(64 + j)}) {item}", styles["ItemText"]))

            story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        buffer.seek(0)
        return buffer
    except ValidationError:
        raise
    except Exception as exc:
        raise OperationError(f"Erro ao gerar PDF da prova: {exc}") from exc



def generate_answer_sheet(student_name: str, student_id: str, num_questions: int = 10, num_itens: int = 5):
    """
    Gera um gabarito idêntico ao template fornecido
    
    Args:
        out_path: Caminho para salvar o PDF
        student_name: Nome do aluno
        num_questions: Número total de questões (padrão 10)
    """
    if not student_name.strip():
        raise ValidationError("O nome do aluno não pode estar vazio para gerar o gabarito.")
    if student_id is None or not str(student_id).strip():
        raise ValidationError("O ID do aluno é obrigatório para gerar o gabarito.")
    if num_questions <= 0:
        raise ValidationError("O número de questões deve ser maior que zero.")
    if num_itens <= 0:
        raise ValidationError("O número de alternativas deve ser maior que zero.")
    if num_itens > 5:
        raise ValidationError("O gabarito automático suporta no máximo 5 alternativas por questão.")

    try:
        layout = build_answer_sheet_layout(num_questions, num_itens)
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        margin_left = 20 * mm
        margin_right = 15 * mm
        header_top = height - 20 * mm
        grid_top = height - 52 * mm
        grid_bottom = 18 * mm
        grid_left = 38 * mm
        available_width = width - grid_left - margin_right
        available_height = grid_top - grid_bottom
        scale = min(
            available_width / layout.total_width,
            available_height / layout.total_height,
        )
        if scale <= 0:
            raise ValidationError("Não foi possível calcular o layout do gabarito.")

        outer_width = layout.total_width * scale
        outer_height = layout.total_height * scale
        outer_x = grid_left
        outer_y = grid_top - outer_height
        options = [chr(64 + j) for j in range(1, num_itens + 1)]

        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_left, header_top, "Aluno: " + student_name)
        c.drawString(margin_left, height - 26 * mm, "ID: " + str(student_id))

        c.setLineWidth(2)
        c.rect(outer_x, outer_y, outer_width, outer_height, stroke=1, fill=0)

        c.setLineWidth(1)

        c.setFont("Helvetica", 11)
        for block in layout.blocks:
            block_x = outer_x + block.x * scale
            block_y = outer_y + outer_height - ((block.y + block.height) * scale)
            row_height = (block.height * scale) / block.question_count
            col_width = (block.width * scale) / num_itens
            circle_radius = max(4, min(row_height, col_width) * 0.22)

            option_label_y = block_y + block.height * scale + 5
            for option_index, option in enumerate(options):
                center_x = block_x + (option_index + 0.5) * col_width
                c.drawCentredString(center_x, option_label_y, option)

            for question_offset in range(block.question_count):
                global_question_number = block.start_index + question_offset + 1
                center_y = block_y + block.height * scale - ((question_offset + 0.5) * row_height)
                c.drawRightString(block_x - 6, center_y - 4, f"Q{global_question_number}")

                for option_index in range(num_itens):
                    center_x = block_x + (option_index + 0.5) * col_width
                    c.circle(center_x, center_y, circle_radius)

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer
    except ValidationError:
        raise
    except Exception as exc:
        raise OperationError(f"Erro ao gerar gabarito em PDF: {exc}") from exc

if __name__ == '__main__':
    pdf_test_generate("prova_aluno.pdf", "Prova de Matemática", [
        {
            'enunciation': 'Qual é a raiz quadrada de 16?',
            'itens': ['2', '4', '8', '16', '32'],
            'correct_item': 1
        },
        {
            'enunciation': 'Qual é o valor de pi?',
            'itens': ['3.14', '3.15', '3.16', '3.17', '3.18'],
            'correct_item': 0
        }
    ], "Lazaro Claubert Souza Rodrigues Oliveira")
    generate_answer_sheet("gabarito_aluno.pdf", "Lazaro Claubert Souza Rodrigues Oliveira", '1', 5,4)
