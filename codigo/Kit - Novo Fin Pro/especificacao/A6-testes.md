# Anexo A6 — Testes automatizados

> Gerado automaticamente por `ferramentas/gerar_especificacao.py` em 10/10/2026 16:12. Não edite à mão: rode o gerador.

Total: **273 testes** em `tests/`. Rodar: `.venv\Scripts\python -m pytest`.

## `test_admin.py` (2)

> Senha de administrador: protege a importação de boletos, inclusive contra acesso direto à API.

- `test_importacao_so_abre_com_a_senha_de_administrador` — importacao so abre com a senha de administrador
- `test_bloqueio_por_tentativas_e_fim_das_sessoes` — bloqueio por tentativas e fim das sessoes

## `test_api.py` (5)

> Testes ponta a ponta da API com boletos gerados (PDF com texto e foto girada via OCR).

- `test_status` — status
- `test_fluxo_pdf_lancamento_duplicidade_e_consultas` — fluxo pdf lancamento duplicidade e consultas
- `test_linha_digitada` — linha digitada
- `test_foto_girada_com_ocr` — foto girada com ocr
- `test_arquivo_invalido` — arquivo invalido

## `test_api_melhorias.py` (5)

> Leitura em segundo plano, lançamento em lote, gravação pendente e senha de acesso.

- `test_leitura_em_segundo_plano_com_progresso` — leitura em segundo plano com progresso
- `test_tarefa_com_arquivo_invalido` — tarefa com arquivo invalido
- `test_lancamento_em_lote` — lancamento em lote
- `test_planilha_aberta_no_excel_nao_segura_lancamentos` — Com o banco de dados, o lançamento é gravado na hora; a planilha Excel é atualizada quando for fechada.
- `test_senha_de_acesso_para_aparelhos_da_rede` — senha de acesso para aparelhos da rede

## `test_backup.py` (9)

> Backup automático para fora do computador (OneDrive, Google Drive, pen drive).

- `test_copia_planilha_arquivos_e_configuracoes` — copia planilha arquivos e configuracoes
- `test_avisa_quando_o_backup_atrasa_ou_falha` — avisa quando o backup atrasa ou falha
- `test_api_do_backup_exige_administrador` — api do backup exige administrador
- `test_sugere_pastas_de_nuvem` — sugere pastas de nuvem
- `test_backup_total_leva_codigo_versoes_e_todas_as_configuracoes` — backup total leva codigo versoes e todas as configuracoes
- `test_pacote_completo_em_zip_e_conferencia` — pacote completo em zip e conferencia
- `test_restaura_tudo_em_outro_computador` — restaura tudo em outro computador
- `test_agendador_faz_o_backup_do_dia_e_o_pacote_da_semana` — agendador faz o backup do dia e o pacote da semana
- `test_api_do_pacote_e_da_conferencia` — api do pacote e da conferencia

## `test_banco.py` (4)

> Banco de dados SQLite com a planilha Excel gerada automaticamente (e edições do Excel trazidas de volta).

- `test_primeira_abertura_importa_a_planilha_existente` — primeira abertura importa a planilha existente
- `test_grava_no_banco_e_gera_a_planilha` — grava no banco e gera a planilha
- `test_planilha_aberta_no_excel_nao_trava_lancamentos` — planilha aberta no excel nao trava lancamentos
- `test_edicao_no_excel_volta_para_o_sistema_sem_desfazer_o_que_o_sistema_gravou` — edicao no excel volta para o sistema sem desfazer o que o sistema gravou

## `test_bot.py` (3)

> Comandos do bot do Telegram (/vencidos, /hoje, /semana, /buscar, /previsao, /resumo).

- `test_comandos_listam_com_linha_digitavel_e_pix_copia_e_cola` — comandos listam com linha digitavel e pix copia e cola
- `test_listas_grandes_sao_divididas` — listas grandes sao divididas
- `test_bot_responde_so_para_cadastrados` — bot responde so para cadastrados

## `test_busca_comprovantes.py` (7)

> Central de comprovantes: busca em todas as partes, filtros, permissões e ZIP.

- `test_junta_comprovantes_de_todas_as_partes` — junta comprovantes de todas as partes
- `test_filtros_por_nome_valor_data_e_numero` — filtros por nome valor data e numero
- `test_pagos_sem_comprovante` — pagos sem comprovante
- `test_numero_curto_nao_procura_dentro_da_linha_digitavel` — numero curto nao procura dentro da linha digitavel
- `test_permissoes_escondem_empresas_e_caixa` — permissoes escondem empresas e caixa
- `test_zip_com_os_comprovantes_filtrados` — zip com os comprovantes filtrados
- `test_api_busca_e_zip` — api busca e zip

## `test_caixa.py` (17)

> Caixa: entradas e saídas em dinheiro, períodos, relatórios, leitura do cupom, bot do caixa e aba Gastos.

- `test_periodos_dia_semana_mes_e_ano` — periodos dia semana mes e ano
- `test_lanca_entrada_e_saida_e_valida` — lanca entrada e saida e valida
- `test_resumo_do_periodo_com_saldo_e_onde_mais_se_gastou` — resumo do periodo com saldo e onde mais se gastou
- `test_filtro_por_dia_semana_e_ano` — filtro por dia semana e ano
- `test_gastos_em_dinheiro_entram_na_analise_de_gastos` — gastos em dinheiro entram na analise de gastos
- `test_gastos_em_dinheiro_entram_no_fechamento_do_mes` — gastos em dinheiro entram no fechamento do mes
- `test_le_o_valor_a_pagar_e_nao_o_troco` — le o valor a pagar e nao o troco
- `test_recibo_simples_sem_rotulo` — recibo simples sem rotulo
- `test_foto_do_cupom_vira_conversa_e_fica_pronta_para_revisar` — foto do cupom vira conversa e fica pronta para revisar
- `test_revisar_na_tela_lanca_no_caixa_com_o_comprovante` — revisar na tela lanca no caixa com o comprovante
- `test_cadastrar_um_centro_de_custo_novo_pelo_bot` — cadastrar um centro de custo novo pelo bot
- `test_digitar_o_nome_do_centro_tambem_funciona` — digitar o nome do centro tambem funciona
- `test_pergunta_o_valor_quando_nao_consegue_ler` — pergunta o valor quando nao consegue ler
- `test_quem_nao_esta_nos_outros_bots_e_recusado` — quem nao esta nos outros bots e recusado
- `test_cancelar_desiste_do_gasto` — cancelar desiste do gasto
- `test_a_mesma_foto_nao_entra_duas_vezes` — a mesma foto nao entra duas vezes
- `test_api_do_caixa_e_gastos_em_dinheiro` — api do caixa e gastos em dinheiro

## `test_codigo.py` (10)

- `test_boleto_bancario_real_valido` — boleto bancario real valido
- `test_conversao_linha_barras_ida_e_volta` — conversao linha barras ida e volta
- `test_detecta_digito_verificador_invalido` — detecta digito verificador invalido
- `test_correcao_de_um_digito` — correcao de um digito
- `test_correcao_de_dois_digitos_em_campos_diferentes` — correcao de dois digitos em campos diferentes
- `test_correcao_prioriza_confusoes_tipicas_de_ocr` — correcao prioriza confusoes tipicas de ocr
- `test_fator_de_vencimento_novo_ciclo` — fator de vencimento novo ciclo
- `test_arrecadacao_modulo_10_e_11` — arrecadacao modulo 10 e 11
- `test_formatacao` — formatacao
- `test_tamanho_invalido` — tamanho invalido

## `test_comprovante.py` (6)

> Comprovantes de pagamento: reconhecer, achar o boleto/Pix, registrar pago com juros e desconto (tela, anexo e bot).

- `test_reconhece_comprovantes_e_nao_confunde_com_boleto` — reconhece comprovantes e nao confunde com boleto
- `test_escolhe_o_lancamento_so_quando_tem_certeza` — escolhe o lancamento so quando tem certeza
- `test_juros_e_desconto_pelo_valor_pago` — juros e desconto pelo valor pago
- `test_comprovante_enviado_na_tela_registra_o_pagamento` — comprovante enviado na tela registra o pagamento
- `test_anexar_comprovante_marca_como_pago_com_os_valores` — anexar comprovante marca como pago com os valores
- `test_caixa_de_entrada_registra_comprovante_e_responde` — caixa de entrada registra comprovante e responde

## `test_corpus.py` (8)

> Regressão sobre o corpus variado: PDFs de layouts diferentes, guias, carnê, scan e fotos de papel.

- `test_bancario_com_rotulos_na_mesma_linha` — bancario com rotulos na mesma linha
- `test_conta_de_consumo_sem_rotulo_beneficiario` — conta de consumo sem rotulo beneficiario
- `test_guia_das_beneficiario_e_orgao_arrecadador` — guia das beneficiario e orgao arrecadador
- `test_carne_com_tres_boletos_na_pagina` — carne com tres boletos na pagina
- `test_pdf_escaneado_sem_texto` — pdf escaneado sem texto
- `test_pdf_escaneado_deitado` — Caso real: folha escaneada girada 90° dentro da página do PDF.
- `test_foto_de_papel_com_perspectiva` — foto de papel com perspectiva
- `test_foto_de_conta_de_consumo` — foto de conta de consumo

## `test_demonstracao.py` (3)

> Versão de demonstração: dados de exemplo completos e nenhum envio para fora.

- `test_dados_de_exemplo_cobrem_todas_as_telas` — dados de exemplo cobrem todas as telas
- `test_usuarios_e_bots_ja_vem_configurados` — usuarios e bots ja vem configurados
- `test_na_demonstracao_nada_e_enviado_para_fora` — na demonstracao nada e enviado para fora

## `test_deposito_cheque.py` (5)

> Comprovante de depósito de cheque (banco): não é a foto do cheque — acha o cheque pela CMC-7 e dá a baixa.

- `test_cmc7_nas_posicoes_certas` — cmc7 nas posicoes certas
- `test_comprovante_de_deposito_nao_e_cheque` — comprovante de deposito nao e cheque
- `test_bot_da_baixa_no_cheque_depositado` — bot da baixa no cheque depositado
- `test_cheque_nao_encontrado_fica_para_conferir` — cheque nao encontrado fica para conferir
- `test_depositei_pela_tela_com_comprovante` — depositei pela tela com comprovante

## `test_desktop_cache.py` (1)

> Depois de uma atualização, a janela do aplicativo não pode continuar mostrando telas antigas do cache.

- `test_limpa_cache_da_janela_somente_quando_as_telas_mudam` — limpa cache da janela somente quando as telas mudam

## `test_diesel.py` (23)

> Diesel: compras, abastecimentos, saldo, médias por máquina, relatórios, leitura dos canhotos e o bot do diesel.

- `test_saldo_compras_menos_abastecimentos` — saldo compras menos abastecimentos
- `test_consumo_pelo_horimetro_e_pelo_km` — consumo pelo horimetro e pelo km
- `test_periodos_semana_quinzena_e_mes` — periodos semana quinzena e mes
- `test_maquina_pela_placa_e_renomear_leva_os_abastecimentos` — maquina pela placa e renomear leva os abastecimentos
- `test_texto_do_relatorio` — texto do relatorio
- `test_le_o_canhoto` — le o canhoto
- `test_le_o_comprovante_da_compra_e_a_legenda_decide` — le o comprovante da compra e a legenda decide
- `test_canhoto_vai_para_o_responsavel_escolher_a_maquina` — canhoto vai para o responsavel escolher a maquina
- `test_canhoto_sem_litros_pergunta_e_placa_marca_a_maquina` — canhoto sem litros pergunta e placa marca a maquina
- `test_nova_maquina_pelo_telegram_e_saldo_baixo` — nova maquina pelo telegram e saldo baixo
- `test_compra_pelo_bot_com_botao_de_1000_litros` — compra pelo bot com botao de 1000 litros
- `test_arquivo_sem_tipo_pergunta_e_repetido_e_recusado` — arquivo sem tipo pergunta e repetido e recusado
- `test_conferencia_na_tela` — conferencia na tela
- `test_relatorios_automaticos` — relatorios automaticos
- `test_api_do_diesel` — api do diesel
- `test_le_as_duas_linhas_do_canhoto_e_acerta_pelo_rodape` — le as duas linhas do canhoto e acerta pelo rodape
- `test_reconhece_o_combustivel` — reconhece o combustivel
- `test_preco_da_tabela_e_saldo_por_combustivel` — preco da tabela e saldo por combustivel
- `test_lancar_canhoto_com_duas_linhas` — lancar canhoto com duas linhas
- `test_bot_pergunta_a_maquina_de_cada_linha` — bot pergunta a maquina de cada linha
- `test_api_le_o_arquivo_e_lanca_pela_tela` — api le o arquivo e lanca pela tela
- `test_comprovante_do_banco_tira_o_posto_de_quem_recebeu` — comprovante do banco tira o posto de quem recebeu
- `test_saldo_em_reais_com_s10_e_comum_no_mesmo_canhoto` — A semana: 1.000 L pagos no preço do S10 (R$ 7.450) e o canhoto do Posto City com 200 L de cada combustível.

## `test_diesel_relatorio.py` (6)

> Relatório do diesel em três níveis (simples, detalhado e completo): contas, textos do Telegram, API e Excel.

- `test_analise_compara_mostra_trechos_e_pontos_de_atencao` — analise compara mostra trechos e pontos de atencao
- `test_periodo_passado_nao_tem_previsao` — periodo passado nao tem previsao
- `test_tres_niveis_de_texto` — tres niveis de texto
- `test_texto_longo_e_cortado_para_o_telegram` — texto longo e cortado para o telegram
- `test_comando_do_bot_e_nivel_dos_automaticos` — comando do bot e nivel dos automaticos
- `test_api_do_relatorio_e_excel_completo` — api do relatorio e excel completo

## `test_empresas.py` (16)

> Módulo Empresas: cadastro, fechamento por período, baixa automática, cheques e relatório.

- `test_a_nota_entra_no_fechamento_pelo_dia_20` — a nota entra no fechamento pelo dia 20
- `test_identifica_a_empresa_por_cnpj_nome_ou_apelido` — identifica a empresa por cnpj nome ou apelido
- `test_nao_deixa_cadastrar_duas_empresas_com_o_mesmo_nome` — nao deixa cadastrar duas empresas com o mesmo nome
- `test_renomear_a_empresa_leva_junto_as_notas` — renomear a empresa leva junto as notas
- `test_fechamento_junta_as_notas_do_periodo` — fechamento junta as notas do periodo
- `test_valor_total_sai_da_quantidade_vezes_o_unitario` — valor total sai da quantidade vezes o unitario
- `test_comprovante_com_o_numero_da_nf_da_baixa_so_naquela_nota` — comprovante com o numero da nf da baixa so naquela nota
- `test_pagamento_parcial_deixa_a_nota_parcial_e_mostra_quanto_falta` — pagamento parcial deixa a nota parcial e mostra quanto falta
- `test_sem_numero_de_nf_o_valor_baixa_as_notas_mais_antigas` — sem numero de nf o valor baixa as notas mais antigas
- `test_sobra_vira_credito_e_cancelar_devolve_tudo` — sobra vira credito e cancelar devolve tudo
- `test_recebimento_descobre_a_empresa_pelo_numero_da_nota` — recebimento descobre a empresa pelo numero da nota
- `test_cheque_prende_as_notas_do_pedido_e_libera_ao_compensar` — cheque prende as notas do pedido e libera ao compensar
- `test_cheque_devolvido_solta_as_notas` — cheque devolvido solta as notas
- `test_cheques_a_depositar_viram_avisos_de_vencimento` — cheques a depositar viram avisos de vencimento
- `test_relatorio_sai_no_formato_da_planilha_usada_hoje` — relatorio sai no formato da planilha usada hoje
- `test_resumo_das_empresas_mostra_atraso_e_cheques` — resumo das empresas mostra atraso e cheques

## `test_empresas_api.py` (8)

> API do módulo Empresas: cadastro, notas, cheques, recebimentos, fechamento e importação do print.

- `test_cadastro_de_empresa_e_resumo` — cadastro de empresa e resumo
- `test_fechamento_em_json_excel_e_pdf` — fechamento em json excel e pdf
- `test_mover_a_nota_para_outro_fechamento` — A NF chegou depois do dia 20: dá para mandá-la para o fechamento seguinte, com todas as suas linhas.
- `test_recebimento_da_baixa_e_pode_ser_cancelado` — recebimento da baixa e pode ser cancelado
- `test_cheque_pela_api_prende_e_solta_as_notas` — cheque pela api prende e solta as notas
- `test_analisar_arquivo_e_importar_print_do_fechamento` — analisar arquivo e importar print do fechamento
- `test_conferencia_da_caixa_de_entrada_do_bot` — conferencia da caixa de entrada do bot
- `test_config_do_bot_de_notas_esconde_o_token` — config do bot de notas esconde o token

## `test_empresas_bot.py` (16)

> Bot de notas fiscais: recebimento pelo Telegram, baixa automática, conferência, comandos e envio do fechamento.

- `test_nota_em_xml_e_lancada_sozinha_no_fechamento_da_empresa` — nota em xml e lancada sozinha no fechamento da empresa
- `test_a_mesma_nota_nao_entra_duas_vezes` — a mesma nota nao entra duas vezes
- `test_empresa_nova_e_cadastrada_sozinha_ao_receber_a_nota` — empresa nova e cadastrada sozinha ao receber a nota
- `test_comprovante_de_pix_da_baixa_e_responde_quanto_falta` — comprovante de pix da baixa e responde quanto falta
- `test_cheque_escaneado_fica_guardado_com_os_dados_do_cmc7` — cheque escaneado fica guardado com os dados do cmc7
- `test_cheque_fotografado_e_reconhecido_pelo_cnpj_e_prende_os_pedidos` — Foto de cheque como o escritório manda: sem legenda, o sistema descobre tudo sozinho.
- `test_comprovante_de_deposito_compensa_o_cheque_do_mesmo_valor` — comprovante de deposito compensa o cheque do mesmo valor
- `test_comprovante_sem_empresa_espera_conferencia` — comprovante sem empresa espera conferencia
- `test_print_do_fechamento_fica_para_importar` — print do fechamento fica para importar
- `test_arquivo_desconhecido_vira_erro_com_explicacao` — arquivo desconhecido vira erro com explicacao
- `test_conferencia_lanca_o_que_o_robo_nao_teve_certeza` — conferencia lanca o que o robo nao teve certeza
- `test_dinheiro_que_chega_antes_da_nota_vira_credito_e_baixa_sozinho` — dinheiro que chega antes da nota vira credito e baixa sozinho
- `test_descartar_tira_da_conferencia` — descartar tira da conferencia
- `test_varias_pessoas_podem_mandar_arquivos_para_o_bot` — O bot de notas aceita arquivos de todo mundo que estiver liberado — não só de uma pessoa.
- `test_comandos_respondem_fechamento_empresas_e_cheques` — comandos respondem fechamento empresas e cheques
- `test_envio_automatico_do_fechamento_no_dia_20` — envio automatico do fechamento no dia 20

## `test_empresas_leitura.py` (12)

> Leitura dos arquivos do bot de notas: NF-e (XML e DANFE), cheque, comprovante e print do fechamento.

- `test_le_a_nota_fiscal_pelo_xml` — le a nota fiscal pelo xml
- `test_le_o_danfe_pelo_texto` — le o danfe pelo texto
- `test_numero_da_nota_sai_da_chave_de_acesso` — No DANFE fotografado o número impresso às vezes sai errado; a chave de acesso não deixa dúvida.
- `test_analisar_reconhece_o_xml_sem_precisar_de_ocr` — analisar reconhece o xml sem precisar de ocr
- `test_le_o_cheque_pela_linha_cmc7_e_pelos_rotulos` — le o cheque pela linha cmc7 e pelos rotulos
- `test_le_a_foto_de_um_cheque_de_verdade` — Frente e verso fotografados: valor, "bom para" à mão, dados da conta e os pedidos do verso.
- `test_data_escrita_a_mao_aceita_ruido_do_ocr` — data escrita a mao aceita ruido do ocr
- `test_numeros_soltos_do_cheque_nao_viram_pedidos` — Conta, cooperativa e endereço não podem ser confundidos com a lista de pedidos do verso.
- `test_cmc7_fora_de_ordem_nao_quebra` — cmc7 fora de ordem nao quebra
- `test_le_o_comprovante_de_pix_com_as_notas_citadas` — le o comprovante de pix com as notas citadas
- `test_numeros_de_nf_e_pedido_na_legenda` — numeros de nf e pedido na legenda
- `test_le_o_print_do_fechamento_linha_por_linha` — le o print do fechamento linha por linha

## `test_entrada.py` (5)

> Caixa de entrada: boletos recebidos por e-mail (IMAP) e pelo bot do Telegram (sem acessar a internet).

- `test_anexos_do_email_ignora_logotipos_e_textos` — anexos do email ignora logotipos e textos
- `test_email_le_anexos_sem_alterar_a_caixa_e_sem_repetir` — email le anexos sem alterar a caixa e sem repetir
- `test_primeira_verificacao_sem_emails_recentes_comeca_do_ultimo` — primeira verificacao sem emails recentes comeca do ultimo
- `test_telegram_recebe_so_de_pessoas_cadastradas_e_responde` — telegram recebe so de pessoas cadastradas e responde
- `test_api_da_caixa_de_entrada` — api da caixa de entrada

## `test_fechamento.py` (3)

> Fechamento do mês para o contador (Excel, PDF e ZIP com comprovantes).

- `test_totais_por_vencimento_e_por_pagamento` — totais por vencimento e por pagamento
- `test_zip_para_o_contador_com_comprovantes` — zip para o contador com comprovantes
- `test_api_do_fechamento` — api do fechamento

## `test_gravacao.py` (2)

> Fila de gravação: planilha aberta no Excel não perde lançamentos nem alterações.

- `test_lancamentos_e_alteracoes_aguardam_e_sao_gravados_ao_fechar_o_excel` — lancamentos e alteracoes aguardam e sao gravados ao fechar o excel
- `test_cancelar_lancamento_que_aguarda_gravacao` — cancelar lancamento que aguarda gravacao

## `test_harmonizacao.py` (2)

> Nome do beneficiário pelo CPF/CNPJ: histórico da planilha e consenso dentro do arquivo.

- `test_consenso_no_mesmo_arquivo_corrige_leitura_ruim` — consenso no mesmo arquivo corrige leitura ruim
- `test_historico_da_planilha_prevalece_e_preenche_ausente` — historico da planilha prevalece e preenche ausente

## `test_ia.py` (3)

> Integração com IA usando um cliente Anthropic simulado (sem rede).

- `test_extrair_monta_pedido_e_le_json` — extrair monta pedido e le json
- `test_recusa_vira_erro` — recusa vira erro
- `test_endpoint_mescla_e_valida_linha_da_ia` — endpoint mescla e valida linha da ia

## `test_importacao.py` (5)

> Importação de boletos exportados de outros sistemas (CSV, Excel e ".xls" em HTML).

- `test_conversao_de_valores_datas_e_situacao` — conversao de valores datas e situacao
- `test_reconhece_colunas_e_confere_as_linhas_de_um_csv` — reconhece colunas e confere as linhas de um csv
- `test_planilha_excel_com_titulo_acima_das_colunas` — planilha excel com titulo acima das colunas
- `test_xls_gerado_em_html_por_outros_sistemas` — xls gerado em html por outros sistemas
- `test_importacao_pela_api` — importacao pela api

## `test_juros_visiveis.py` (3)

> Juros e multas pagos aparecem nos totais das listas, no Painel e em Gastos.

- `test_resumo_da_lista_soma_os_juros_dos_pagos` — resumo da lista soma os juros dos pagos
- `test_painel_mostra_os_juros_pagos_no_mes` — painel mostra os juros pagos no mes
- `test_gastos_mostra_os_juros_do_periodo` — gastos mostra os juros do periodo

## `test_notificacoes.py` (13)

> Lembretes de vencimento: regras, mensagens, agendador (dia do vencimento 3x), agenda, configuração e API.

- `test_regras_de_alerta` — regras de alerta
- `test_mensagem_lista_os_boletos_e_numero_do_lembrete` — mensagem lista os boletos e numero do lembrete
- `test_tres_lembretes_no_dia_do_vencimento` — tres lembretes no dia do vencimento
- `test_pago_encerra_os_lembretes` — pago encerra os lembretes
- `test_sistema_ligado_tarde_envia_so_o_horario_mais_recente` — sistema ligado tarde envia so o horario mais recente
- `test_regras_antes_vencidos_canais_e_dias_da_semana` — regras antes vencidos canais e dias da semana
- `test_falha_em_todos_os_canais_tenta_de_novo_depois` — falha em todos os canais tenta de novo depois
- `test_agenda_mostra_os_proximos_lembretes` — agenda mostra os proximos lembretes
- `test_configuracao_valida_regras_e_mascara_segredos` — configuracao valida regras e mascara segredos
- `test_migra_configuracao_da_versao_anterior` — migra configuracao da versao anterior
- `test_enviar_agora_e_teste` — enviar agora e teste
- `test_inicializacao_com_windows` — inicializacao com windows
- `test_api_de_notificacoes` — api de notificacoes

## `test_permissoes.py` (9)

> Administrador por usuário, permissões por pessoa e login pedido toda vez que o aplicativo abre.

- `test_administrador_entra_e_cadastra_sem_a_senha_de_administrador` — administrador entra e cadastra sem a senha de administrador
- `test_nao_deixa_ficar_sem_administrador` — nao deixa ficar sem administrador
- `test_usuario_comum_so_faz_o_que_foi_liberado` — usuario comum so faz o que foi liberado
- `test_permissoes_extras_liberam_as_telas` — permissoes extras liberam as telas
- `test_estado_do_acesso_mostra_perfil_e_permissoes` — estado do acesso mostra perfil e permissoes
- `test_usuarios_antigos_continuam_podendo_o_que_podiam` — Arquivo criado antes das permissões: ninguém perde acesso de uma hora para outra.
- `test_ao_abrir_o_aplicativo_so_o_computador_precisa_entrar_de_novo` — ao abrir o aplicativo so o computador precisa entrar de novo
- `test_login_pedido_toda_vez_que_o_aplicativo_abre` — login pedido toda vez que o aplicativo abre
- `test_desligar_o_login_no_computador_desliga_o_pedido_ao_abrir` — desligar o login no computador desliga o pedido ao abrir

## `test_pix.py` (3)

> Pix: validação das chaves e leitura/geração do Copia e Cola (inclusive por QR code em imagem).

- `test_validacao_das_chaves` — validacao das chaves
- `test_gera_e_le_pix_copia_e_cola` — gera e le pix copia e cola
- `test_le_pix_de_uma_imagem_com_qr_code` — le pix de uma imagem com qr code

## `test_pix_centros_api.py` (10)

> Pix, centros de custo, análise de gastos e endpoints do aplicativo de desktop.

- `test_lanca_edita_e_lista_pix` — lanca edita e lista pix
- `test_pix_copia_e_cola_e_duplicado` — pix copia e cola e duplicado
- `test_centros_de_custo_e_renomear` — centros de custo e renomear
- `test_analise_de_gastos` — analise de gastos
- `test_analise_por_mes_agrupa_centros_menores` — analise por mes agrupa centros menores
- `test_notificacoes_incluem_pix` — notificacoes incluem pix
- `test_migra_planilha_antiga` — migra planilha antiga
- `test_endpoints_do_aplicativo` — endpoints do aplicativo
- `test_painel_mostra_boletos_e_pix_vencidos` — painel mostra boletos e pix vencidos
- `test_previsao_de_saidas_por_semana` — previsao de saidas por semana

## `test_planilha.py` (4)

- `test_ciclo_completo` — ciclo completo
- `test_lote_em_uma_gravacao_e_aba_historico` — lote em uma gravacao e aba historico
- `test_ignora_status_desconhecido_e_linhas_vazias` — ignora status desconhecido e linhas vazias
- `test_voltar_para_pendente_apaga_a_data_de_pagamento_gravada` — Regressão: apagar um campo precisa limpar a célula (antes a data de pagamento antiga ficava na planilha).

## `test_rede.py` (5)

> Acesso pelo celular: senha com hash, servidor de rede liga/desliga, login, bloqueio, sair e QR code.

- `test_senha_guardada_com_hash_e_troca_invalida_sessoes` — senha guardada com hash e troca invalida sessoes
- `test_liga_e_desliga_o_servidor_da_rede_sem_reiniciar` — liga e desliga o servidor da rede sem reiniciar
- `test_login_do_celular_bloqueio_sair_e_permissoes` — login do celular bloqueio sair e permissoes
- `test_qrcode_do_endereco` — qrcode do endereco
- `test_utilitarios_de_rede` — utilitarios de rede

## `test_registro_log.py` (1)

> O arquivo de log gira quando fica grande e guarda só alguns arquivos antigos.

- `test_log_gira_e_limita_arquivos` — log gira e limita arquivos

## `test_relatorio_geral.py` (5)

> Relatório geral do mês (menu Relatórios): pagos, juros e multas, últimos 12 meses e as partes de cada módulo.

- `test_pagos_juros_e_historico_do_mes` — pagos juros e historico do mes
- `test_sem_permissao_de_gastos_nao_mostra_os_pagamentos` — sem permissao de gastos nao mostra os pagamentos
- `test_uma_parte_com_erro_nao_derruba_o_relatorio` — uma parte com erro nao derruba o relatorio
- `test_excel_tem_resumo_juros_e_12_meses` — excel tem resumo juros e 12 meses
- `test_api_do_relatorio_geral` — api do relatorio geral

## `test_resumo_semanal.py` (6)

> Resumos da semana: segunda (o que vence) e sexta (o que foi pago), agendamento, envio e API.

- `test_resumo_de_segunda_lista_o_que_vence_na_semana` — resumo de segunda lista o que vence na semana
- `test_resumo_de_sexta_soma_o_que_foi_pago` — resumo de sexta soma o que foi pago
- `test_semana_vazia_nao_quebra` — semana vazia nao quebra
- `test_resumo_sai_uma_vez_no_dia_e_no_horario` — resumo sai uma vez no dia e no horario
- `test_resumo_desligado_ou_sem_canal` — resumo desligado ou sem canal
- `test_api_de_previa_e_envio` — api de previa e envio

## `test_saude.py` (1)

> Tela Saúde do sistema: diagnóstico sempre responde e aponta o que precisa de atenção.

- `test_diagnostico_e_acoes` — diagnostico e acoes

## `test_sino.py` (2)

> Sininho: avisos vistos saem da contagem; dispensados saem da lista; voltam quando a situação muda.

- `test_avisos_vistos_dispensados_e_mudanca_de_situacao` — avisos vistos dispensados e mudanca de situacao
- `test_api_do_sininho` — api do sininho

## `test_telas.py` (4)

> Testes das telas no navegador (Playwright + Edge já instalado no Windows).

- `test_todas_as_telas_abrem_sem_erro` — todas as telas abrem sem erro
- `test_ler_boleto_lancar_e_dar_baixa_por_comprovante` — ler boleto lancar e dar baixa por comprovante
- `test_painel_mostra_previsao_e_vencidos` — painel mostra previsao e vencidos
- `test_empresas_importa_o_print_do_fechamento_e_da_baixa` — Parte 5 do módulo Empresas: começar a operar com o fechamento que já estava em andamento.

## `test_telegram_destinatarios.py` (4)

> Telegram para várias pessoas e grupos do escritório.

- `test_configuracao_antiga_com_um_chat_vira_lista` — configuracao antiga com um chat vira lista
- `test_salva_destinatarios_sem_repetidos_nem_invalidos` — salva destinatarios sem repetidos nem invalidos
- `test_envia_para_todos_os_ativos_e_informa_quem_nao_recebeu` — envia para todos os ativos e informa quem nao recebeu
- `test_procura_pessoas_e_grupos_que_falaram_com_o_bot` — procura pessoas e grupos que falaram com o bot

## `test_texto.py` (8)

- `test_extratores_basicos` — extratores basicos
- `test_limpeza_do_beneficiario_casos_reais` — limpeza do beneficiario casos reais
- `test_frases_com_a_palavra_beneficiario_nao_viram_nome` — frases com a palavra beneficiario nao viram nome
- `test_nome_em_duas_linhas_e_instrucoes_com_beneficiario` — nome em duas linhas e instrucoes com beneficiario
- `test_datas_por_extenso_ligaduras_e_guias` — datas por extenso ligaduras e guias
- `test_linha_com_ruido_de_ocr` — linha com ruido de ocr
- `test_segmentacao_de_ocr_sem_espacos` — segmentacao de ocr sem espacos
- `test_campos_por_posicao_rotulo_acima_e_valor_a_direita` — campos por posicao rotulo acima e valor a direita

## `test_usuarios.py` (3)

> Usuários do escritório: login por pessoa, quem lançou/pagou, comprovante e histórico de cada boleto.

- `test_login_por_pessoa_registra_quem_lancou_pagou_e_anexou` — login por pessoa registra quem lancou pagou e anexou
- `test_exigir_login_tambem_no_computador` — exigir login tambem no computador
- `test_bloqueio_apos_senhas_erradas` — bloqueio apos senhas erradas

## `test_versao.py` (6)

> Controle de versão: número, histórico (VERSOES.md), guardar uma versão nova, voltar a uma antiga e a API.

- `test_proxima_versao_por_tipo` — proxima versao por tipo
- `test_historico_e_registro_no_topo` — historico e registro no topo
- `test_guardar_versao_nova` — guardar versao nova
- `test_voltar_para_uma_versao_antiga_sem_perder_nada` — voltar para uma versao antiga sem perder nada
- `test_historico_completo_num_arquivo_para_o_backup` — historico completo num arquivo para o backup
- `test_api_da_versao` — api da versao
