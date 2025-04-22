from io import BytesIO
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

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
    pdfmetrics.registerFont(TTFont('Arial', 'app/api/dependencies/ARIAL.TTF'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'app/api/dependencies/ARIALBD.TTF'))
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    styles.add(ParagraphStyle(
        name='QuestionTitle',
        parent=styles['Normal'],
        fontName='Arial-Bold',
        fontSize=12,
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        name='QuestionText',
        parent=styles['Normal'],
        fontName='Arial',
        fontSize=11,
        leading=14,
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='ItemText',
        parent=styles['Normal'],
        fontName='Arial',
        fontSize=11,
        leftIndent=12,
        spaceAfter=6
    ))
    
    # Conteúdo da prova
    story = []
    
    # Cabeçalho da prova
    story.append(Paragraph(test_name, styles['Title']))
    story.append(Paragraph(f"Aluno: {student_name}  ID: {student_id}", styles['QuestionTitle']))
    story.append(Spacer(1, 0.5 * inch))
    
    # Adiciona questões
    for i, question in enumerate(questions, 1):
        story.append(Paragraph(f"Questão {i}", styles['QuestionTitle']))
        story.append(Paragraph(question['enunciation'], styles['QuestionText']))
        
        # Adiciona itens (alternativas)
        for j, item in enumerate(question['itens'], 1):
            story.append(Paragraph(f"{chr(64 + j)}) {item}", styles['ItemText']))
        
        story.append(Spacer(1, 0.2 * inch))
        

    # Gera o PDF
    doc.build(story)

    buffer.seek(0)

    return buffer



from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

def generate_answer_sheet(student_name: str, student_id: str, num_questions: int = 10, num_itens: int = 5):
    """
    Gera um gabarito idêntico ao template fornecido
    
    Args:
        out_path: Caminho para salvar o PDF
        student_name: Nome do aluno
        num_questions: Número total de questões (padrão 10)
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    box_width = 40*num_itens  # Largura da caixa
    box_height = 25.2 * num_questions  # Altura da caixa
    circle_start_x = 40 * mm  # Posição inicial (margem da borda esquerda)
    circle_spacing = 15 * mm  # Espaçamento entre os círculos
    circle_radius = 5  # Raio dos círculos
    options = [chr(64 + j) for j in range(1, num_itens + 1)]
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, height-20*mm, "Aluno: " + student_name)
    c.drawString(18.5*mm, height-26*mm," ID: " + student_id)
    
    # Opções de resposta (A-E)
    c.setFont("Helvetica", 12)
    options_y = height-40*mm
    for i, option in enumerate(options):
        c.drawString(35*mm + i*15*mm, options_y, f"{option}")
    
    # Números das questões em uma coluna
    c.setFont("Helvetica", 10)
    start_y = options_y - 2*mm
    
    for i in range(1, num_questions + 1):
        c.drawString(20*mm, start_y - i*9*mm, f"Q{i}")
    
    x = 100  # Posição X do canto inferior esquerdo
    y = (options_y - box_height) - 20 # Posição Y do canto inferior esquerdo

    c.setLineWidth(2)
    c.rect(x, y, box_width, box_height, stroke=1, fill=0)
    c.setLineWidth(1)
    for j in range(1, num_questions + 1):
        for i in range(1, num_itens + 1):
            c.circle(circle_start_x + (i - 1) * circle_spacing, start_y - 9 * mm * j, circle_radius)
    
    
    c.showPage()  # Finaliza a página 2
    c.save()
    buffer.seek(0)  # Move o ponteiro para o início do buffer
    return buffer

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