"""
Mesclador Universal Pro
Um aplicativo GUI para mesclar múltiplos arquivos de texto ou código em um único arquivo.
Suporta drag-and-drop, pré-visualização de arquivos, personalização de separadores e exportação em diferentes formatos.

Dependências:
- tkinter
- tkinterdnd2
- chardet
- PIL (para ícones)
- ttkbootstrap (opcional, para tema visual)
- reportlab (opcional, para exportação em PDF)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, Menu
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import chardet
import logging
from typing import List, Dict, Optional
import threading
import queue
import re
import json
from PIL import Image, ImageTk

# Tenta importar ttkbootstrap para estilização visual
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    USE_TTKBOOTSTRAP = True
except ImportError:
    USE_TTKBOOTSTRAP = False

# Tenta importar reportlab para suporte a PDF
try:
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Configuração do logging para registrar eventos e erros
logging.basicConfig(
    filename='merger.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constantes
MAX_FILE_SIZE_MB = 10  # Tamanho máximo de arquivo permitido para mesclagem (em MB)
SETTINGS_FILE = "settings.json"  # Arquivo para armazenar configurações do usuário
VALID_EXTENSIONS = (
    '.txt', '.md', '.log', '.py', '.js', '.html', '.css', '.json', '.xml',
    '.csv', '.ini', '.cfg', '.bat', '.sh', '.java', '.c', '.cpp', '.h',
    '.php', '.rb', '.go', '.rs', '.ts', '.jsx', '.tsx', '.yml', '.yaml',
    '.toml', '.sql', '.pl', '.swift', '.m', '.vb', '.ps1', '.lua', '.r',
    '.scala', '.groovy', '.dart', '.kt', '.kts', '.gradle', '.makefile',
    '.dockerfile', '.txt', '.log', '.md'
)  # Extensões de arquivo suportadas

def sanitize_filename(filename: str) -> str:
    """
    Remove caracteres inválidos de nomes de arquivos para garantir compatibilidade.

    Args:
        filename (str): Nome do arquivo a ser sanitizado.

    Returns:
        str: Nome do arquivo com caracteres inválidos substituídos por '_'.

    Example:
        >>> sanitize_filename("teste<invalido>.txt")
        'teste_invalido_.txt'
    """
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

class FileMergerApp(TkinterDnD.Tk if not USE_TTKBOOTSTRAP else ttkb.Window):
    """
    Classe principal do aplicativo Mesclador Universal Pro.
    Cria uma interface gráfica para mesclar arquivos de texto ou código.

    Attributes:
        selected_files (List[Dict]): Lista de dicionários com informações dos arquivos selecionados.
        _merge_thread (Optional[threading.Thread]): Thread para mesclagem em segundo plano.
        _queue (queue.Queue): Fila para comunicação entre thread de mesclagem e UI.
        settings (Dict): Configurações carregadas do arquivo settings.json.
    """

    def __init__(self):
        """
        Inicializa o aplicativo, configurando a janela principal e a interface do usuário.

        Raises:
            Exception: Se houver falha na inicialização da interface ou carregamento de configurações.
        """
        if USE_TTKBOOTSTRAP:
            super().__init__(themename="darkly")  # Usa tema 'darkly' do ttkbootstrap
        else:
            super().__init__()  # Usa Tkinter padrão
        self.title("Mesclador Universal Pro")
        self.geometry("850x650")  # Tamanho inicial da janela
        self.minsize(700, 500)  # Tamanho mínimo da janela
        self.selected_files: List[Dict] = []  # Armazena arquivos selecionados
        self._merge_thread: Optional[threading.Thread] = None  # Thread de mesclagem
        self._queue = queue.Queue()  # Fila para atualizações de progresso
        self._load_settings()  # Carrega configurações do usuário
        self._setup_ui()  # Configura a interface do usuário
        self._bind_shortcuts()  # Vincula atalhos de teclado

    def _setup_ui(self):
        """
        Configura os componentes da interface do usuário, incluindo menus, botões, treeview,
        área de pré-visualização e opções de saída.

        Raises:
            Exception: Se houver falha ao carregar ícones ou configurar widgets.
        """
        if not USE_TTKBOOTSTRAP:
            self.style = ttk.Style(self)
            self.style.theme_use('clam')  # Tema padrão do ttk

        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Barra de menu
        menubar = Menu(self)
        self.config(menu=menubar)
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self._show_help)

        # Treeview para lista de arquivos com cores alternadas
        self.tree = ttk.Treeview(
            main_frame,
            columns=('file', 'size'),
            show='headings',
            selectmode='browse'
        )
        self.tree.heading('file', text='Arquivo', command=lambda: self._sort_files('file'))
        self.tree.heading('size', text='Tamanho (KB)', command=lambda: self._sort_files('size'))
        self.tree.column('file', width=500)
        self.tree.column('size', width=100, anchor='center')
        self.tree.tag_configure('oddrow', background='#f0f0f0')
        self.tree.tag_configure('evenrow', background='#ffffff')

        # Barra de rolagem vertical
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Frame para botões
        btn_frame = ttk.Frame(main_frame)
        self.btn_add = ttk.Button(btn_frame, text="Adicionar arquivos", command=self._select_files)
        self.btn_remove = ttk.Button(btn_frame, text="Remover arquivo", command=self._remove_file)
        self.btn_clear = ttk.Button(btn_frame, text="Limpar lista", command=self._clear_files)

        # Carrega ícones (se disponíveis)
        try:
            self.icon_add = ImageTk.PhotoImage(Image.open("icons/add_icon.png").resize((20, 20)))
            self.icon_remove = ImageTk.PhotoImage(Image.open("icons/remove_icon.png").resize((20, 20)))
            self.icon_clear = ImageTk.PhotoImage(Image.open("icons/clear_icon.png").resize((20, 20)))
            self.icon_merge = ImageTk.PhotoImage(Image.open("icons/merge_icon.png").resize((20, 20)))
            self.btn_add.config(image=self.icon_add, compound=tk.LEFT)
            self.btn_remove.config(image=self.icon_remove, compound=tk.LEFT)
            self.btn_clear.config(image=self.icon_clear, compound=tk.LEFT)
        except Exception:
            # Ignora falha ao carregar ícones
            pass

        # Tooltips para botões
        self._create_tooltip(self.btn_add, "Adicionar arquivos para mesclar (suporta múltiplos)")
        self._create_tooltip(self.btn_remove, "Remover o arquivo selecionado da lista")
        self._create_tooltip(self.btn_clear, "Limpar todos os arquivos da lista")

        # Área de pré-visualização
        self.preview = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, state='disabled')

        # Frame para opções de saída
        options_frame = ttk.LabelFrame(main_frame, text="Configurações de Saída")
        ttk.Label(options_frame, text="Nome do arquivo de saída:").pack(side=tk.LEFT, padx=5, pady=5)
        self.output_name = ttk.Entry(options_frame, width=30)
        self.output_name.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(options_frame, text="Formato:").pack(side=tk.LEFT, padx=(10,5), pady=5)
        formats = ['TXT', 'MD', 'HTML']
        if REPORTLAB_AVAILABLE:
            formats.append('PDF')
        self.output_format = ttk.Combobox(options_frame, values=formats, state='readonly', width=5)
        self.output_format.set(self.settings.get("format", 'TXT'))
        self.output_format.pack(side=tk.LEFT, padx=5, pady=5)

        # Frame para personalização do separador
        sep_frame = ttk.LabelFrame(main_frame, text="Separador entre arquivos")
        self.separator_entry = ttk.Entry(sep_frame, width=60)
        self.separator_entry.insert(0, self.settings.get("separator", "\n" + "="*50 + "\nARQUIVO: {filename}\n" + "="*50 + "\n\n"))
        self.separator_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self._create_tooltip(self.separator_entry, "Use {filename} para inserir o nome do arquivo no separador")

        # Barra de progresso
        self.progress = ttk.Progressbar(main_frame, mode='determinate')

        # Botão de mesclagem
        self.btn_merge = ttk.Button(main_frame, text="Mesclar arquivos", command=self._start_merge)
        try:
            self.btn_merge.config(image=self.icon_merge, compound=tk.LEFT)
        except Exception:
            pass
        self._create_tooltip(self.btn_merge, "Iniciar o processo de mesclagem dos arquivos selecionados")

        # Layout em grade
        self.tree.grid(row=0, column=0, sticky='nsew', pady=(0,5))
        scrollbar.grid(row=0, column=1, sticky='ns', pady=(0,5))
        btn_frame.grid(row=1, column=0, sticky='w', pady=5)
        self.btn_add.pack(side=tk.LEFT, padx=2)
        self.btn_remove.pack(side=tk.LEFT, padx=2)
        self.btn_clear.pack(side=tk.LEFT, padx=2)
        self.preview.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=5)
        options_frame.grid(row=3, column=0, sticky='w', pady=5)
        sep_frame.grid(row=4, column=0, sticky='w', pady=5)
        self.progress.grid(row=5, column=0, columnspan=2, sticky='ew', pady=5)
        self.btn_merge.grid(row=6, column=0, sticky='ew', pady=10)

        # Configura pesos para redimensionamento
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Vincula eventos
        self.tree.bind('<<TreeviewSelect>>', self._show_preview)

        # Habilita drag-and-drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._handle_drop)

    def _create_tooltip(self, widget, text):
        """
        Cria um tooltip para um widget.

        Args:
            widget: Widget ao qual o tooltip será associado.
            text (str): Texto a ser exibido no tooltip.
        """
        tooltip = Tooltip(widget, text)
        widget.bind("<Enter>", tooltip.show)
        widget.bind("<Leave>", tooltip.hide)

    def _bind_shortcuts(self):
        """
        Vincula atalhos de teclado para ações comuns.
        - Ctrl+O: Adicionar arquivos
        - Ctrl+M: Iniciar mesclagem
        """
        self.bind("<Control-o>", lambda e: self._select_files())
        self.bind("<Control-m>", lambda e: self._start_merge())

    def _select_files(self):
        """
        Abre um diálogo para selecionar arquivos a serem mesclados.

        Chama _add_files para processar os arquivos selecionados.
        """
        files = filedialog.askopenfilenames(
            title="Selecione arquivos",
            filetypes=[("Todos os arquivos", "*.*")]
        )
        self._add_files(files)

    def _add_files(self, files: List[str]):
        """
        Adiciona arquivos à lista de arquivos selecionados, verificando formato e tamanho.

        Args:
            files (List[str]): Lista de caminhos de arquivos a serem adicionados.

        Raises:
            Exception: Se houver erro ao acessar ou processar um arquivo.
        """
        for file_path in files:
            if os.path.isdir(file_path):
                # Adiciona recursivamente arquivos de uma pasta
                for root, _, filenames in os.walk(file_path):
                    full_paths = [os.path.join(root, f) for f in filenames if f.lower().endswith(VALID_EXTENSIONS)]
                    self._add_files(full_paths)
                continue
            if not any(f['path'] == file_path for f in self.selected_files):
                if not file_path.lower().endswith(VALID_EXTENSIONS):
                    messagebox.showwarning("Formato inválido", f"{file_path} não é um arquivo de texto ou código suportado.")
                    continue
                try:
                    size_kb = os.path.getsize(file_path) / 1024
                    if size_kb > MAX_FILE_SIZE_MB * 1024:
                        messagebox.showwarning("Arquivo muito grande",
                                             f"O arquivo {os.path.basename(file_path)} excede o tamanho máximo de {MAX_FILE_SIZE_MB}MB e será ignorado.")
                        continue
                    encoding = self._detect_encoding(file_path)
                    self.selected_files.append({'path': file_path, 'size': size_kb, 'encoding': encoding})
                except Exception as e:
                    logging.error(f"Erro ao adicionar arquivo {file_path}: {e}")
        self._refresh_file_list()

    def _refresh_file_list(self):
        """
        Atualiza a Treeview com a lista de arquivos selecionados, aplicando cores alternadas.
        """
        self.tree.delete(*self.tree.get_children())
        for i, f in enumerate(self.selected_files):
            filename = os.path.basename(f['path'])
            size_str = f"{f['size']:.1f}"
            tag = 'oddrow' if i % 2 == 0 else 'evenrow'
            self.tree.insert('', 'end', values=(filename, size_str), tags=(tag,))

    def _remove_file(self):
        """
        Remove o arquivo selecionado da lista e atualiza a interface.
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Remover arquivo", "Selecione um arquivo para remover.")
            return
        index = self.tree.index(selected[0])
        del self.selected_files[index]
        self._refresh_file_list()
        self.preview.config(state='normal')
        self.preview.delete('1.0', tk.END)
        self.preview.config(state='disabled')

    def _clear_files(self):
        """
        Limpa todos os arquivos da lista e a área de pré-visualização.
        """
        self.selected_files.clear()
        self._refresh_file_list()
        self.preview.config(state='normal')
        self.preview.delete('1.0', tk.END)
        self.preview.config(state='disabled')

    def _show_preview(self, event=None):
        """
        Exibe uma pré-visualização do conteúdo do arquivo selecionado.

        Args:
            event: Evento de seleção na Treeview (opcional).

        Raises:
            Exception: Se houver erro ao ler o arquivo.
        """
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        file_info = self.selected_files[index]
        try:
            with open(file_info['path'], 'r', encoding=file_info['encoding'] or 'utf-8', errors='replace') as f:
                content = f.read(10000)  # Limita pré-visualização a 10k caracteres
            self.preview.config(state='normal')
            self.preview.delete('1.0', tk.END)
            self.preview.insert(tk.END, content)
            self.preview.config(state='disabled')
        except Exception as e:
            self.preview.config(state='normal')
            self.preview.delete('1.0', tk.END)
            self.preview.insert(tk.END, f"Erro ao carregar preview: {e}")
            self.preview.config(state='disabled')

    def _detect_encoding(self, file_path: str) -> Optional[str]:
        """
        Detecta a codificação de um arquivo usando a biblioteca chardet.

        Args:
            file_path (str): Caminho do arquivo.

        Returns:
            Optional[str]: Codificação detectada ou None se houver erro.

        Raises:
            Exception: Se houver erro ao ler o arquivo.
        """
        try:
            with open(file_path, 'rb') as f:
                rawdata = f.read(10000)
            result = chardet.detect(rawdata)
            return result['encoding']
        except Exception as e:
            logging.error(f"Erro ao detectar encoding do arquivo {file_path}: {e}")
            return None

    def _handle_drop(self, event):
        """
        Processa arquivos arrastados e soltos na janela.

        Args:
            event: Evento de drag-and-drop contendo os caminhos dos arquivos.
        """
        files = self.tk.splitlist(event.data)
        self._add_files(files)

    def _sort_files(self, column: str):
        """
        Ordena a lista de arquivos com base na coluna especificada.

        Args:
            column (str): Coluna para ordenação ('file' ou 'size').
        """
        reverse = False
        if hasattr(self, '_last_sort_column') and self._last_sort_column == column:
            reverse = not getattr(self, '_last_sort_reverse', False)
        if column == 'size':
            self.selected_files.sort(key=lambda x: x[column], reverse=reverse)
        else:
            self.selected_files.sort(key=lambda x: os.path.basename(x['path']).lower(), reverse=reverse)
        self._last_sort_column = column
        self._last_sort_reverse = reverse
        self._refresh_file_list()

    def _start_merge(self):
        """
        Inicia o processo de mesclagem, verificando entradas e iniciando thread de mesclagem.

        Raises:
            Exception: Se houver erro ao acessar diretórios ou salvar o arquivo.
        """
        if not self.selected_files:
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado para mesclar.")
            return
        output_name = self.output_name.get().strip()
        if not output_name:
            messagebox.showwarning("Aviso", "Informe o nome do arquivo de saída.")
            return
        output_name = sanitize_filename(output_name)
        ext = self.output_format.get().lower()
        if not output_name.lower().endswith(f".{ext}"):
            output_name += f".{ext}"

        # Diálogo para escolher local de salvamento
        initialdir = self.settings.get("last_save_dir", os.path.expanduser("~"))
        filetypes = [(f"Arquivos {ext.upper()}", f"*.{ext}")]
        output_path = filedialog.asksaveasfilename(
            title="Salvar arquivo mesclado",
            initialdir=initialdir,
            initialfile=output_name,
            filetypes=filetypes,
            defaultextension=f".{ext}"
        )

        if not output_path:
            messagebox.showinfo("Cancelado", "A mesclagem foi cancelada.")
            return

        # Atualiza diretório de salvamento nas configurações
        self.settings["last_save_dir"] = os.path.dirname(output_path)
        self._save_settings()

        total_size = sum(f['size'] for f in self.selected_files)
        if total_size > 100 * 1024:  # Aviso para arquivos maiores que 100MB
            if not messagebox.askyesno("Aviso de tamanho", "A mesclagem pode ser lenta devido ao tamanho total dos arquivos. Deseja continuar?"):
                return

        # Desativa interface durante processamento
        self._set_ui_state('disabled')
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.selected_files)

        # Inicia mesclagem em thread separada
        self._merge_thread = threading.Thread(target=self._merge_files, args=(output_path, ext))
        self._merge_thread.start()
        self.after(100, self._check_thread)

    def _set_ui_state(self, state: str):
        """
        Define o estado (ativado/desativado) dos widgets da interface.

        Args:
            state (str): Estado desejado ('normal' ou 'disabled').
        """
        widgets = [self.btn_add, self.btn_remove, self.btn_clear, self.btn_merge,
                   self.output_name, self.output_format, self.separator_entry]
        for w in widgets:
            w.config(state=state)
        if state == 'disabled':
            self.tree.configure(selectmode='none')
        else:
            self.tree.configure(selectmode='browse')

    def _check_thread(self):
        """
        Verifica mensagens da thread de mesclagem e atualiza a interface.

        Raises:
            queue.Empty: Se a fila estiver vazia, agenda nova verificação.
        """
        try:
            while True:
                msg = self._queue.get_nowait()
                if isinstance(msg, int):
                    self.progress['value'] = msg
                    self.title(f"Mesclador Universal Pro - Processando arquivo {msg}/{len(self.selected_files)}")
                elif msg == 'success':
                    self._set_ui_state('normal')
                    self.progress['value'] = 0
                    self.title("Mesclador Universal Pro")
                    messagebox.showinfo("Sucesso", "Arquivos mesclados com sucesso!")
                else:
                    self._set_ui_state('normal')
                    self.progress['value'] = 0
                    self.title("Mesclador Universal Pro")
                    messagebox.showerror("Erro", f"Erro durante a mesclagem: {msg}")
        except queue.Empty:
            if self._merge_thread.is_alive():
                self.after(100, self._check_thread)
            else:
                self._set_ui_state('normal')
                self.progress['value'] = 0
                self.title("Mesclador Universal Pro")

    def _merge_files(self, output_file: str, ext: str):
        """
        Realiza a mesclagem dos arquivos no formato especificado.

        Args:
            output_file (str): Caminho do arquivo de saída.
            ext (str): Extensão do formato de saída ('txt', 'md', 'html', 'pdf').

        Raises:
            PermissionError: Se não houver permissão para escrever no diretório.
            Exception: Para outros erros durante a mesclagem.
        """
        try:
            separator_template = self.separator_entry.get()
            if ext == 'pdf' and REPORTLAB_AVAILABLE:
                self._merge_to_pdf(output_file, separator_template)
            else:
                output_dir = os.path.dirname(output_file) or "."
                if not os.access(output_dir, os.W_OK):
                    raise PermissionError(f"Sem permissão para escrever em {output_dir}")
                with open(output_file, 'w', encoding='utf-8') as outfile:
                    for idx, file_info in enumerate(self.selected_files, start=1):
                        filename = os.path.basename(file_info['path'])
                        separator = separator_template.replace("{filename}", filename)
                        outfile.write(separator)
                        try:
                            with open(file_info['path'], 'r', encoding=file_info['encoding'] or 'utf-8', errors='replace') as infile:
                                while True:
                                    chunk = infile.read(65536)  # Lê em blocos de 64KB
                                    if not chunk:
                                        break
                                    outfile.write(chunk)
                        except Exception as e:
                            logging.error(f"Erro ao ler arquivo {file_info['path']}: {e}")
                            outfile.write(f"\nErro ao ler o arquivo: {e}\n")
                        self._queue.put(idx)
                self._queue.put('success')
        except PermissionError as e:
            logging.error(f"Erro de permissão: {e}")
            self._queue.put(f"Sem permissão para salvar em {os.path.dirname(output_file)}. Escolha outro local.")
        except Exception as e:
            logging.error(f"Erro na mesclagem: {e}")
            self._queue.put(str(e))

    def _merge_to_pdf(self, output_file: str, separator_template: str):
        """
        Mescla arquivos em um documento PDF usando reportlab.

        Args:
            output_file (str): Caminho do arquivo PDF de saída.
            separator_template (str): Modelo do separador entre arquivos.

        Raises:
            Exception: Se houver erro ao ler arquivos ou gerar o PDF.
        """
        c = canvas.Canvas(output_file)
        y = 800
        for idx, file_info in enumerate(self.selected_files, start=1):
            filename = os.path.basename(file_info['path'])
            separator = separator_template.replace("{filename}", filename)
            c.drawString(50, y, separator.strip())
            y -= 20
            try:
                with open(file_info['path'], 'r', encoding=file_info['encoding'] or 'utf-8', errors='replace') as infile:
                    for line in infile:
                        c.drawString(50, y, line.strip())
                        y -= 15
                        if y < 50:
                            c.showPage()
                            y = 800
            except Exception as e:
                logging.error(f"Erro ao ler arquivo {file_info['path']}: {e}")
                c.drawString(50, y, f"Erro ao ler o arquivo: {e}")
                y -= 20
            self._queue.put(idx)
        c.save()
        self._queue.put('success')

    def _load_settings(self):
        """
        Carrega as configurações do usuário a partir do arquivo settings.json.

        Raises:
            Exception: Se houver erro ao ler o arquivo de configurações.
        """
        self.settings = {"last_save_dir": os.path.expanduser("~")}  # Diretório padrão
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings.update(json.load(f))
        except FileNotFoundError:
            pass
        except Exception as e:
            logging.error(f"Erro ao carregar configurações: {e}")

    def _save_settings(self):
        """
        Salva as configurações do usuário no arquivo settings.json.

        Raises:
            Exception: Se houver erro ao escrever no arquivo de configurações.
        """
        self.settings["separator"] = self.separator_entry.get()
        self.settings["format"] = self.output_format.get()
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            logging.error(f"Erro ao salvar configurações: {e}")

    def _show_help(self):
        """
        Exibe uma janela com informações de ajuda sobre o aplicativo.
        """
        messagebox.showinfo("Ajuda", "Mesclador Universal Pro\nVersão 1.0\n\n"
                            "Use Ctrl+O para adicionar arquivos\n"
                            "Use Ctrl+M para iniciar a mesclagem\n\n"
                            "Suporta arquivos .txt, .md, .log\n"
                            "Arraste e solte arquivos ou pastas para adicionar.\n\n"
                            "Desenvolvido por você.")

class Tooltip:
    """
    Classe para criar tooltips flutuantes em widgets.

    Attributes:
        widget: Widget associado ao tooltip.
        text (str): Texto do tooltip.
        tipwindow: Janela flutuante do tooltip (None se não exibida).
    """

    def __init__(self, widget, text):
        """
        Inicializa o tooltip.

        Args:
            widget: Widget ao qual o tooltip será associado.
            text (str): Texto a ser exibido no tooltip.
        """
        self.widget = widget
        self.text = text
        self.tipwindow = None

    def show(self, event=None):
        """
        Exibe o tooltip na posição do cursor.

        Args:
            event: Evento de entrada do mouse (opcional).
        """
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide(self, event=None):
        """
        Oculta o tooltip.

        Args:
            event: Evento de saída do mouse (opcional).
        """
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

if __name__ == "__main__":
    """
    Ponto de entrada do aplicativo.
    Cria uma instância do FileMergerApp e inicia o loop principal da interface.
    """
    app = FileMergerApp()
    app.mainloop()