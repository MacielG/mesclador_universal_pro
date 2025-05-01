# Mesclador Universal Pro

Mesclador Universal Pro é uma ferramenta GUI para mesclar múltiplos arquivos de texto em um único arquivo, com suporte a diferentes formatos e personalização.

## Funcionalidades

- Mesclagem de arquivos com separadores personalizáveis
- Suporte a drag-and-drop de arquivos e pastas
- Visualização de conteúdo antes da mesclagem
- Exportação para formatos TXT, MD, HTML e PDF (PDF requer reportlab)
- Salvamento automático das configurações do usuário (separador, formato)
- Feedback de progresso detalhado durante a mesclagem
- Atalhos de teclado (Ctrl+O para adicionar arquivos, Ctrl+M para mesclar)
- Interface moderna com ttkbootstrap (se instalado)
- Validação de tipos de arquivo suportados (.txt, .md, .log)
- Tratamento amigável de erros

## Instalação

Recomenda-se criar um ambiente virtual Python e instalar as dependências:

```bash
pip install tkinterdnd2 chardet pillow
pip install ttkbootstrap  # opcional para tema moderno
pip install reportlab      # opcional para exportar PDF
```

## Uso

Execute o script principal:

```bash
python mesclador_universal_pro.py
```

- Use o botão "Adicionar arquivos" ou arraste e solte arquivos/pastas na janela.
- Configure o nome do arquivo de saída, formato e separador.
- Clique em "Mesclar arquivos" para iniciar.
- Use Ctrl+O para abrir o seletor de arquivos e Ctrl+M para iniciar a mesclagem.
- Veja o progresso na barra e no título da janela.

## Capturas de Tela

![Interface principal](screenshots/main.png)

## Tecnologias Usadas

- Python 3
- Tkinter e tkinterdnd2 para GUI e drag-and-drop
- ttkbootstrap para tema moderno (opcional)
- Pillow para ícones (opcional)
- chardet para detecção de encoding
- reportlab para exportação PDF (opcional)

## Licença

MIT License

## Contato

Desenvolvido por Guilherme Maciel. Para dúvidas ou sugestões, entre em contato: guilherme_costantino@hotmail.com
