-- Inserir conteúdos (abstraídos)
INSERT INTO content (id, name) VALUES
(1, 'Potência com expoente zero'),
(2, 'Potência com expoente negativo'),
(3, 'Multiplicação de potências de mesma base'),
(4, 'Radiciação como potência de expoente fracionário'),
(5, 'Crescimento exponencial'),
(6, 'Potência de radicais'),
(7, 'Divisão de potências de mesma base'),
(8, 'Comparação entre potências'),
(9, 'Potência de potência'),
(10, 'Resolução de equações com potências'),
(11, 'Algoritmo para exponenciação');

-- Inserir questões
INSERT INTO question (id, enunciation, itens, correct_item, level, contents) VALUES
(1, 'Quanto vale 5⁰?', ARRAY['0', '1', '5', 'indefinido'], 1, 1, ARRAY[]::VARCHAR[]),
(2, 'Qual é o valor de 2⁻³?', ARRAY['8', '1/8', '-8', '3'], 1, 1, ARRAY[]::VARCHAR[]),
(3, 'Quanto é 2³ × 2²?', ARRAY['2⁵', '2⁶', '4⁵', '2'], 0, 2, ARRAY[]::VARCHAR[]),
(4, 'Qual o valor de √(a) em termos de potência?', ARRAY['a¹', 'a¹ᐟ²', 'a²', '1/a'], 1, 2, ARRAY[]::VARCHAR[]),
(5, 'Se a população de uma cidade dobra a cada ano, e hoje há 1.000 pessoas, quantas haverá em 3 anos?', ARRAY['2.000', '3.000', '8.000', '1.000'], 2, 3, ARRAY[]::VARCHAR[]),
(6, 'Se x = √(16), qual o valor de x³?', ARRAY['64', '8', '16', '4'], 0, 3, ARRAY[]::VARCHAR[]),
(7, 'Simplifique a expressão: (2³ × 2²) ÷ 2⁴', ARRAY['2', '2³', '2⁵', '2¹'], 3, 2, ARRAY[]::VARCHAR[]),
(8, 'Qual número é maior: 3⁵ ou 5³?', ARRAY['3⁵', '5³', 'iguais', 'não é possível saber'], 0, 4, ARRAY[]::VARCHAR[]),
(9, 'Quanto vale (2²)³?', ARRAY['2⁵', '2⁶', '2³', '2⁴'], 1, 2, ARRAY[]::VARCHAR[]),
(10, 'Uma bactéria triplica a cada hora. Se havia 10 bactérias às 12h, quantas haverá às 15h?', ARRAY['30', '90', '270', '810'], 3, 3, ARRAY[]::VARCHAR[]),
(11, 'Se 2^x = 16, qual o valor de x?', ARRAY['2', '4', '8', '16'], 1, 3, ARRAY[]::VARCHAR[]),
(12, 'Implemente um algoritmo que calcule a potência de um número base elevado a um expoente n (baseⁿ).', ARRAY['função com loop multiplicando', 'somar base n vezes', 'multiplicar base por n', 'usar raiz quadrada'], 0, 6, ARRAY[]::VARCHAR[]);

-- Criar teste
INSERT INTO test (id) VALUES (1);

-- Relacionar questões ao teste
INSERT INTO test_question (test_id, question_id) VALUES
(1, 1),
(1, 2),
(1, 3),
(1, 4),
(1, 5),
(1, 6),
(1, 7),
(1, 8),
(1, 9),
(1, 10),
(1, 11),
(1, 12);

-- Relacionar questões aos conteúdos
INSERT INTO question_content (question_id, content_id) VALUES
(1, 1),  -- 5^0
(2, 2),  -- 2^-3
(3, 3),  -- multiplicação de potências
(4, 4),  -- raiz quadrada como potência
(5, 5),  -- crescimento exponencial
(6, 4), (6, 6),  -- raiz quadrada + potência
(7, 3), (7, 7),  -- multiplicação e divisão de potências
(8, 8),  -- comparação de potências
(9, 9),  -- potência de potência
(10, 5),  -- crescimento exponencial
(11, 10),  -- equação com potências
(12, 11);  -- algoritmo de exponenciação
