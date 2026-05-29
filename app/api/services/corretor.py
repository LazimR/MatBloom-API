from statistics import mean
from io import BytesIO

import cv2
import numpy as np
import pytesseract as pt

from app.api.services.answer_sheet_layout import build_answer_sheet_layout
from app.api.services import utils
from app.core.exceptions import OperationError, ValidationError

DEBUGAR = False
gabarito = ["a", "b", "c", "d", "e", "a", "b", "c", "d", "e"]
NUMERO_QUESTOES = 10
NUMERO_ALTERNATIVAS = 5

def corrigir(arquivo: BytesIO, gabarito:list = None, numero_questoes=NUMERO_QUESTOES, numero_alternativas=NUMERO_ALTERNATIVAS):
    arquivo.seek(0)

    if gabarito is None:
        raise ValidationError("O gabarito da prova é obrigatório para a correção automática.")
    if numero_questoes <= 0:
        raise ValidationError("O número de questões deve ser maior que zero.")
    if numero_alternativas <= 0:
        raise ValidationError("O número de alternativas deve ser maior que zero.")
    if numero_alternativas > 5:
        raise ValidationError("A correção automática suporta no máximo 5 alternativas por questão.")
    if len(gabarito) != numero_questoes:
        raise ValidationError("O gabarito informado não corresponde ao número de questões da prova.")

    number_to_letter = lambda number: chr(number + 65)    

    imagem_bytes = np.asarray(bytearray(arquivo.read()), dtype=np.uint8)

    try:
        layout = build_answer_sheet_layout(numero_questoes, numero_alternativas)
        img = cv2.imdecode(imagem_bytes, cv2.IMREAD_COLOR)
        if img is None:
            raise ValidationError("A imagem não pôde ser carregada. Verifique o arquivo enviado.")

        img = cv2.resize(img, (1512, 2016))
        img_copy = img.copy()

        roi_id_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        roi_id_thresh = cv2.threshold(roi_id_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        config = "--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789ID:"
        texto_extraido = pt.image_to_string(roi_id_thresh, lang="eng", config=config)

        id_aluno = None
        for linha in texto_extraido.splitlines():
            linha = linha.strip().upper()
            if "ID:" in linha:
                id_str = linha.split("ID:")[-1].strip()
                id_aluno = "".join(filter(str.isdigit, id_str)) or None
                break

        imagem_sem_sombra = utils.remover_sombra(img)
        imagem_cinza = cv2.cvtColor(imagem_sem_sombra, cv2.COLOR_BGR2GRAY)
        imagem_com_desfoque = cv2.GaussianBlur(imagem_cinza, (3, 3), 5)
        imagem_binaria = cv2.threshold(
            imagem_com_desfoque, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )[1]

        contornos, _ = cv2.findContours(
            imagem_binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        retangulos = utils.encontrar_retangulos(contornos)
        if not retangulos:
            raise ValidationError("Não foi possível encontrar a área do gabarito na imagem enviada.")
        maior_retangulo = retangulos[0]
        vertices_maior_retangulo = utils.encontrar_vertices(maior_retangulo)
        vertices_ordenadas = utils.reordenar_pontos(vertices_maior_retangulo)

        if DEBUGAR:
            cv2.drawContours(img_copy, vertices_ordenadas, -1, (255, 0, 0), 60)
            cv2.imshow("img_copy", img_copy)

        vertices_float_32 = np.float32(vertices_ordenadas)
        cv2.drawContours(imagem_binaria, [maior_retangulo], -1, (0, 0, 0), 16)

        template_formato_retangulo = np.float32(
            [
                [0, 0],
                [layout.total_width, 0],
                [0, layout.total_height],
                [layout.total_width, layout.total_height],
            ]
        )
        matriz_de_transformacao = cv2.getPerspectiveTransform(
            vertices_float_32, template_formato_retangulo
        )
        img_corrigida = cv2.warpPerspective(
            imagem_binaria,
            matriz_de_transformacao,
            (layout.total_width, layout.total_height),
        )
        img_bordas_cortadas = utils.cortar_imagem(img_corrigida, 0.99)
        crop_offset_x = (img_corrigida.shape[1] - img_bordas_cortadas.shape[1]) // 2
        crop_offset_y = (img_corrigida.shape[0] - img_bordas_cortadas.shape[0]) // 2

        respostas = []
        pontuacao = 0
        questoes_erradas = []

        if len(layout.blocks) == 1:
            img_linhas = utils.fatiar_vertical(img_bordas_cortadas, numero_questoes)
            blocks_to_process = [(layout.blocks[0], img_linhas)]
        else:
            blocks_to_process = []
            for block in layout.blocks:
                scaled_x = max(0, block.x - crop_offset_x)
                scaled_y = max(0, block.y - crop_offset_y)
                scaled_width = min(block.width, img_bordas_cortadas.shape[1] - scaled_x)
                scaled_height = min(block.height, img_bordas_cortadas.shape[0] - scaled_y)
                if scaled_width <= 0 or scaled_height <= 0:
                    raise ValidationError("Não foi possível localizar corretamente o bloco do gabarito na imagem.")

                block_img = img_bordas_cortadas[
                    scaled_y: scaled_y + scaled_height,
                    scaled_x: scaled_x + scaled_width,
                ]
                block_img = utils.cortar_imagem(block_img, 0.96)
                blocks_to_process.append((block, utils.fatiar_vertical(block_img, block.question_count)))

        for block, img_linhas in blocks_to_process:
            for question_offset, linha in enumerate(img_linhas):
                indice_linha = block.start_index + question_offset
                maior_pixels = 0
                indice_marcado = -1
                img_colunas = utils.fatiar_horizontal(linha, numero_alternativas)
                numero_pixels_na_coluna = []
                for indice_coluna, coluna in enumerate(img_colunas):
                    coluna = utils.cortar_imagem(coluna, 0.90)
                    numero_de_pixels_brancos = cv2.countNonZero(coluna)
                    numero_pixels_na_coluna.append(numero_de_pixels_brancos)
                    if DEBUGAR:
                        cv2.imshow(
                            "imagem_circulo"
                            + str(indice_linha)
                            + "_"
                            + str(indice_coluna)
                            + "_"
                            + str(numero_de_pixels_brancos),
                            coluna,
                        )

                numero_pixels_na_coluna_sem_maior = numero_pixels_na_coluna.copy()
                numero_pixels_na_coluna_sem_maior.remove(max(numero_pixels_na_coluna))
                media_de_pixels = mean(numero_pixels_na_coluna_sem_maior)
                for indice_pixels, pixels in enumerate(numero_pixels_na_coluna):
                    if pixels > maior_pixels and pixels > media_de_pixels * (1.1 + 0.03 * numero_alternativas):
                        maior_pixels = pixels
                        indice_marcado = indice_pixels

                alternativa_em_letra = utils.ober_alternativa_pelo_indice(indice_marcado)
                respostas.append(alternativa_em_letra)

                if indice_marcado == utils.obter_indice_da_alternativa(number_to_letter(gabarito[indice_linha])):
                    pontuacao += 1
                else:
                    questoes_erradas.append(indice_linha + 1)

        if DEBUGAR:
            copia_contornos = img.copy()
            cv2.drawContours(copia_contornos, contornos, -1, (0, 0, 255), 3)
            cv2.drawContours(copia_contornos, [maior_retangulo], -1, (0, 255, 0), 20)
            utils.exibir_imagens([
                ("img", img),
                ("imagem_sem_sombra", imagem_sem_sombra),
                ("imagem_com_desfoque", imagem_com_desfoque),
                ("imagem_binaria", imagem_binaria),
                ("contornos", copia_contornos),
                ("img_corrigida", img_corrigida),
                ("img_bordas_cortadas", img_bordas_cortadas),
            ])
            print("DEBUG Respostas: ", "Arquivo: ", imagem_bytes, respostas, "nota: ", pontuacao, "/ 10")
            print("FIM Debug \n\n\n")
            cv2.waitKey(0)

        letter_to_number = lambda letter: ord(letter.upper()) - 65

        for i, resposta in enumerate(respostas):
            respostas[i] = letter_to_number(resposta)

        return [respostas, pontuacao, id_aluno, questoes_erradas]
    except ValidationError:
        raise
    except Exception as exc:
        raise OperationError(f"Erro ao processar a correção automática do gabarito: {exc}") from exc


if __name__ == "__main__":
    arquivo = 'C:/Users/LazimR/Documents/GitHub/MatBloom/MatBloom-API/app/api/services/gabarito1.jpg'
    respostas, pontuacao, id, questoes_erradas = corrigir(arquivo, ['a','b','c','d','d'],5,4)
    nome_do_estudante = arquivo.replace(
        "gabaritos/", "").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
    print("Estudante: ", nome_do_estudante, "Respostas: ",
          respostas, "Nota: ", pontuacao, "/ 10", "Questões erradas: ", questoes_erradas)
    print("ID: ", id)
