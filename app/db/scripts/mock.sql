TRUNCATE TABLE
    test_response,
    test_question,
    user_classroom,
    question_dependency,
    question_content,
    student,
    test,
    question,
    content,
    classroom,
    "user"
RESTART IDENTITY CASCADE;

INSERT INTO classroom (id, name, school_year, grade_level, shift, active) VALUES
(1, 'Turma Exponenciação A', 2026, '9 ano', 'manha', TRUE),
(2, 'Turma Exponenciação B', 2026, '9 ano', 'tarde', TRUE);

INSERT INTO "user" (id, username, password, email, role) VALUES
(1, 'admin', '$2b$12$pvgcyWmUrBhNFsals962r.NOWpffR5A89P3BxUt.yiH/OgZPMlqti', 'admin@matbloom.com', 'admin'),
(2, 'prof_expo', '$2b$12$pvgcyWmUrBhNFsals962r.NOWpffR5A89P3BxUt.yiH/OgZPMlqti', 'prof.expo@matbloom.com', 'professor'),
(3, 'diretora_maria', '$2b$12$pvgcyWmUrBhNFsals962r.NOWpffR5A89P3BxUt.yiH/OgZPMlqti', 'diretoria@matbloom.com', 'diretor'),
(4, 'prof_expo_b', '$2b$12$pvgcyWmUrBhNFsals962r.NOWpffR5A89P3BxUt.yiH/OgZPMlqti', 'prof.expo.b@matbloom.com', 'professor');

INSERT INTO user_classroom (user_id, classroom_id) VALUES
(2, 1),
(4, 2);

INSERT INTO student (id, name, registration, classroom_id, active) VALUES
(1, 'Lazaro Rodrigues', 'EXP-001', 1, TRUE),
(2, 'Maria Eduarda Silva', 'EXP-002', 1, TRUE),
(3, 'Joao Pedro Santos', 'EXP-003', 1, TRUE),
(4, 'Ana Clara Oliveira', 'EXP-004', 1, TRUE),
(5, 'Gabriel Henrique Souza', 'EXP-005', 1, TRUE),
(6, 'Beatriz Fernandes Lima', 'EXP-006', 1, TRUE),
(7, 'Lucas Matheus Costa', 'EXP-007', 1, TRUE),
(8, 'Mariana Alves Rocha', 'EXP-008', 1, TRUE),
(9, 'Pedro Henrique Martins', 'EXP-009', 1, TRUE),
(10, 'Julia Bezerra Nunes', 'EXP-010', 1, TRUE),
(11, 'Rafael Gomes Pereira', 'EXP-011', 1, TRUE),
(12, 'Camila Araujo Melo', 'EXP-012', 1, TRUE),
(13, 'Isabela Carvalho Sousa', 'EXP-101', 2, TRUE),
(14, 'Matheus Ribeiro Lopes', 'EXP-102', 2, TRUE),
(15, 'Fernanda Castro Lima', 'EXP-103', 2, TRUE),
(16, 'Thiago Almeida Rocha', 'EXP-104', 2, TRUE),
(17, 'Larissa Monteiro Alves', 'EXP-105', 2, TRUE),
(18, 'Bruno Henrique Dias', 'EXP-106', 2, TRUE),
(19, 'Amanda Freitas Moura', 'EXP-107', 2, TRUE),
(20, 'Gustavo Nogueira Silva', 'EXP-108', 2, TRUE);

INSERT INTO content (id, name) VALUES
(1, 'Conceito de potência'),
(2, 'Expoente zero e expoente um'),
(3, 'Leitura e interpretação de potências'),
(4, 'Multiplicação de potências de mesma base'),
(5, 'Divisão de potências de mesma base'),
(6, 'Potência de potência'),
(7, 'Comparação de grandezas exponenciais'),
(8, 'Modelagem de crescimento exponencial'),
(9, 'Justificativa de propriedades de potenciação'),
(10, 'Criação de estratégias com exponenciação');

INSERT INTO question (id, enunciation, itens, correct_item, level) VALUES
(1, 'Qual expressão representa a leitura correta de 2³?', ARRAY['2 multiplicado por ele mesmo 3 vezes', '2 somado 3 vezes', '3 multiplicado por ele mesmo 2 vezes', '2 dividido por 3', '3 dividido por 2'], 0, 1),
(2, 'Qual é o valor de 7¹?', ARRAY['7', '1', '0', '14', '49'], 0, 1),
(3, 'Ao simplificar 5² × 5³, qual propriedade está sendo aplicada corretamente?', ARRAY['Conserva a base e soma os expoentes', 'Multiplica a base e conserva o expoente', 'Subtrai a base e soma os expoentes', 'Eleva a base ao produto dos expoentes', 'Divide os expoentes pela base'], 1, 2),
(4, 'Qual expressão é equivalente a (3²)²?', ARRAY['3² + 3²', '3⁴', '9²', '3² ÷ 2', '2³'], 1, 2),
(5, 'Um tabuleiro recebe o dobro de grãos a cada casa. Qual modelo melhor representa a quantidade na casa n?', ARRAY['2 + n', '2n', 'n²', 'n + 2²', '2ⁿ'], 4, 3),
(6, 'Se um software executa 2³ operações por ciclo e repete esse ciclo 2² vezes, qual é o total de operações?', ARRAY['2⁵', '2⁶', '2³ + 2²', '3²', '8'], 4, 3),
(7, 'Ao comparar 2⁶ e 4³, qual conclusão está correta?', ARRAY['2⁶ é maior', '4³ é maior', 'São equivalentes porque representam 64', 'Não é possível comparar', 'Ambos valem 32'], 4, 4),
(8, 'Em uma cultura de bactérias, a quantidade passa de 3 para 12 e depois para 48. Qual análise melhor descreve o padrão?', ARRAY['Aumenta de 9 em 9', 'Duplica a cada etapa', 'Triplica a cada etapa', 'Quadruplica a cada etapa', 'Multiplica por 4 a cada etapa'], 4, 4),
(9, 'Qual justificativa avalia corretamente a afirmação “a⁰ = 1, para a diferente de zero”?', ARRAY['Porque todo número vezes zero é um', 'Porque zero é o elemento neutro da multiplicação', 'Porque decorre da regularidade da divisão de potências de mesma base', 'Porque o expoente zero anula a base', 'Porque a potência sempre repete a base uma vez'], 4, 5),
(10, 'Qual proposta de solução cria um procedimento eficiente para calcular 3⁸ sem multiplicar 3 oito vezes manualmente?', ARRAY['Somar 3 oito vezes', 'Calcular 3 × 8', 'Usar 3² e depois dividir por 2', 'Transformar em 8³', 'Decompor 3⁸ em (3⁴)² e reutilizar resultados intermediários'], 4, 6);

INSERT INTO question_content (question_id, content_id) VALUES
(1, 1),
(1, 3),
(2, 2),
(3, 4),
(4, 6),
(5, 8),
(6, 4),
(6, 6),
(7, 7),
(8, 8),
(9, 5),
(9, 9),
(10, 6),
(10, 10);

INSERT INTO test (
    id,
    name,
    theme,
    application_date,
    created_by_user_id,
    applied_by_user_id,
    classroom_id,
    student_id,
    source_test_id,
    template_group_id,
    version_number,
    kind,
    visibility,
    target_type
) VALUES
(1, 'Biblioteca Bloom - Exponenciação', 'Exponenciação', NULL, 2, NULL, NULL, NULL, NULL, 1, 1, 'template', 'library', 'turma'),
(2, 'Aplicação OCR - Exponenciação', 'Exponenciação', DATE '2026-04-01', 2, 2, 1, NULL, 1, 1, 1, 'application', 'library', 'turma'),
(3, 'Biblioteca Bloom - Exponenciação v2', 'Exponenciação', NULL, 2, NULL, NULL, NULL, NULL, 1, 2, 'template', 'library', 'turma'),
(4, 'Aplicação Individual - Exponenciação', 'Exponenciação', DATE '2026-04-02', 2, 2, 1, 2, 3, 1, 2, 'application', 'library', 'individual');

INSERT INTO test_question (test_id, question_id) VALUES
(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10),
(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10),
(3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10),
(4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10);

INSERT INTO test_response (id, test_id, student_id, score, responses, wrong_questions, attempt_date) VALUES
(1, 2, 1, 8, ARRAY[0, 0, 1, 1, 4, 4, 2, 4, 4, 4], ARRAY[7, 9], DATE '2026-04-01'),
(2, 2, 2, 7, ARRAY[0, 0, 0, 1, 4, 4, 4, 4, 1, 4], ARRAY[3, 7, 9], DATE '2026-04-01'),
(3, 2, 3, 6, ARRAY[0, 1, 1, 1, 2, 4, 4, 4, 4, 3], ARRAY[2, 5, 7, 10], DATE '2026-04-01'),
(4, 2, 4, 9, ARRAY[0, 0, 1, 1, 4, 4, 4, 4, 2, 4], ARRAY[9], DATE '2026-04-01'),
(5, 2, 5, 5, ARRAY[1, 0, 3, 1, 4, 0, 4, 1, 4, 4], ARRAY[1, 3, 6, 8, 9], DATE '2026-04-01'),
(6, 2, 6, 4, ARRAY[0, 1, 3, 0, 2, 4, 1, 4, 0, 2], ARRAY[2, 3, 4, 5, 7, 9], DATE '2026-04-01'),
(7, 2, 7, 10, ARRAY[0, 0, 1, 1, 4, 4, 4, 4, 4, 4], ARRAY[]::INTEGER[], DATE '2026-04-01'),
(8, 2, 8, 6, ARRAY[0, 0, 1, 3, 4, 2, 4, 4, 4, 1], ARRAY[4, 6, 7, 10], DATE '2026-04-01'),
(9, 2, 9, 7, ARRAY[0, 0, 1, 1, 1, 4, 4, 2, 4, 4], ARRAY[5, 8, 9], DATE '2026-04-01'),
(10, 2, 10, 3, ARRAY[2, 1, 0, 0, 4, 0, 1, 4, 0, 1], ARRAY[1, 2, 3, 4, 6, 7, 9], DATE '2026-04-01'),
(11, 2, 11, 8, ARRAY[0, 0, 1, 1, 4, 4, 4, 2, 4, 4], ARRAY[8, 9], DATE '2026-04-01'),
(12, 2, 12, 5, ARRAY[0, 1, 1, 1, 3, 4, 2, 4, 0, 4], ARRAY[2, 5, 7, 9, 10], DATE '2026-04-01');
