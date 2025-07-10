# PyQt5 관련 모듈 임포트
from PyQt5.QtCore import Qt, QMimeData, QUrl,QTimer,QFileInfo, QDir, QStandardPaths, QPoint,QRect, QSize,QModelIndex, pyqtSignal
from PyQt5.QtGui import QKeySequence, QKeyEvent, QFont,QColor,QPalette # 키보드 이벤트, 폰트, 색상 관련
from PyQt5.QtWidgets import (
    QSplitter, QApplication, QMainWindow, QFileSystemModel, QTreeView, QPushButton, QGridLayout, QColorDialog,
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QMenu, QAction, QDialog, QFileDialog,QStyledItemDelegate,
    QLabel, QScrollArea, QFrame, QSpacerItem, QSizePolicy,QMessageBox,QInputDialog,QAbstractItemView,QStatusBar,QLayout,  QStyle,
    QDialogButtonBox
) # 다양한 UI 위젯들

# 파이썬 기본 모듈 임포트
import os # 운영 체제 관련 기능 (파일 경로, 디렉토리 등)
import shutil # 파일 및 디렉토리 복사, 이동, 삭제 등 고급 파일 작업
import subprocess # 외부 프로세스 실행 (예: 시스템 탐색기 열기)
import sys # 파이썬 인터프리터 관련 기능 (프로그램 종료 등)
import json # JSON 데이터 형식 처리 (설정 파일 저장/로드)
import ctypes # C 데이터 타입과의 호환성 제공 (윈도우 API 호출 등)
import tempfile # 임시 파일 및 디렉토리 생성
import uuid # 범용 고유 식별자 생성 (MAC 주소, 임시 파일 이름 등)
import functools # 고차 함수 및 호출 가능한 객체 작업을 위한 도구 (partial 등)
from win32com.client import Dispatch

# # --- 하드웨어 바인딩 (MAC 주소 기반 접근 제어) ---
# ALLOWED_MACS = [            # getmac: 물리적주소 cmd에서 getmac치면나옴  / hostname: 내컴퓨터이름
#     "D8-5E-D3-01-15-9F",    # MK-39(임경아) PC의 MAC 주소 예시
#     # 여기에 허용할 다른 MAC 주소들을 추가할 수 있습니다.
# ]

class HiddenFileDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        file_path = index.model().filePath(index)
        if QFileInfo(file_path).isHidden():
            option.palette.setColor(QPalette.Text, QColor("gray"))
            option.palette.setColor(QPalette.HighlightedText, QColor("#D3D3D3"))

def get_mac_address():
    mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
    return '-'.join([mac[e:e+2].upper() for e in range(0,12,2)])

def check_hardware():
    mac = get_mac_address()
    if mac not in ALLOWED_MACS:
        QMessageBox.critical(None, "접근 거부", f"이 PC는 승인되지 않았습니다. 관리자에게 문의하세요 (현재 MAC: {mac})")
        sys.exit()
# --- 하드웨어 바인딩 끝 ---

def show_windows_properties(path):
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    SEE_MASK_INVOKEIDLIST = 0x0000000C
    ShellExecuteEx = ctypes.windll.shell32.ShellExecuteExW

    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),("fMask", ctypes.c_ulong),("hwnd", ctypes.c_void_p),
            ("lpVerb", ctypes.c_wchar_p),("lpFile", ctypes.c_wchar_p),("lpParameters", ctypes.c_wchar_p),
            ("lpDirectory", ctypes.c_wchar_p),("nShow", ctypes.c_int),("hInstApp", ctypes.c_void_p),
            ("lpIDList", ctypes.c_void_p),("lpClass", ctypes.c_wchar_p),("hkeyClass", ctypes.c_void_p),
            ("dwHotKey", ctypes.c_ulong),("hIcon", ctypes.c_void_p),("hProcess", ctypes.c_void_p)
        ]

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = SEE_MASK_INVOKEIDLIST
    sei.hwnd = None
    sei.lpVerb = "properties"
    sei.lpFile = path
    sei.lpParameters = None
    sei.lpDirectory = None
    sei.nShow = 1
    sei.hInstApp = None
    ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))

class ExplorerPanel(QWidget):
    request_new_panel = pyqtSignal(str)

    copied_item = None
    cut_item = None
    MAX_UNDO = 10

    def __init__(self, path=''):
        super().__init__()
        self.undo_stack = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        self.folder_label = QLabel()
        font_l = QFont()
        font_l.setBold(True)
        font_l.setPointSize(12)
        self.folder_label.setFont(font_l)
        self.folder_label.setStyleSheet("color: #1a73e8;")
        self.folder_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(self.folder_label)

        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(5)

        btn_font_l = QFont()
        btn_font_l.setPointSize(14)

        def create_button_local(text, tooltip, slot):
            btn = QPushButton(text)
            btn.setFont(btn_font_l)
            btn.setFixedSize(24, 24)
            btn.setToolTip(tooltip)
            btn.clicked.connect(slot)
            return btn

        self.back_button = create_button_local("←", "뒤로가기", self.go_back)
        self.forward_button = create_button_local("→", "앞으로가기", self.go_forward)
        self.up_button = create_button_local("↑", "상위 폴더로 이동", self.go_up)
        top_controls_layout.addWidget(self.back_button)
        top_controls_layout.addWidget(self.forward_button)
        top_controls_layout.addWidget(self.up_button)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("경로를 입력하세요")
        self.path_input.returnPressed.connect(self.on_path_input_change)
        self.path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_controls_layout.addWidget(self.path_input)

        self.delete_button = create_button_local("✕", "탐색기 삭제", self.delete_explorer)
        top_controls_layout.addWidget(self.delete_button)
        main_layout.addLayout(top_controls_layout)

        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden | QDir.System)
        self.model.setRootPath('')
        self.tree = QTreeView()
        self.tree.setDragDropMode(QAbstractItemView.DragDrop)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        hidden_file_delegate = HiddenFileDelegate(self.tree)
        self.tree.setItemDelegate(hidden_file_delegate)
        self.tree.dragEnterEvent = self.custom_tree_dragEnterEvent
        self.tree.setEditTriggers(QTreeView.AllEditTriggers)
        self.tree.setModel(self.model)

        default_dir = QDir.homePath()
        if not path or not os.path.isdir(path):
            path = default_dir

        root_idx = self.model.index(path)
        if not root_idx.isValid() or not self.model.isDir(root_idx) :
            root_idx = self.model.index(default_dir)
        self.tree.setRootIndex(root_idx)

        self.tree.setColumnWidth(0, 250)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.doubleClicked.connect(self.on_double_click)

        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDrop)
        self.tree.setDefaultDropAction(Qt.MoveAction)

        self.tree.dragEnterEvent = self.custom_tree_dragEnterEvent
        self.tree.dragMoveEvent = self.custom_tree_dragMoveEvent
        self.tree.dropEvent = self.custom_tree_dropEvent

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_layout.addWidget(self.tree)

        self.previous_paths = []
        self.forward_paths = []
        self.pending_navigation_path = None
        self.model.directoryLoaded.connect(self.on_directory_loaded)
        self.update_path_input(self.tree.rootIndex())
        self.tree.installEventFilter(self)

    def custom_tree_dragEnterEvent(self, event: QKeyEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            QTreeView.dragEnterEvent(self.tree, event)

    def custom_tree_dragMoveEvent(self, event: QKeyEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            QTreeView.dragMoveEvent(self.tree, event)

    def custom_tree_dropEvent(self, event: QKeyEvent):
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            event.ignore()
            return

        drop_pos = event.pos()
        index_at_drop = self.tree.indexAt(drop_pos)
        destination_folder_path = ""

        if index_at_drop.isValid() and self.model.isDir(index_at_drop):
            destination_folder_path = self.model.filePath(index_at_drop)
        elif index_at_drop.isValid() and not self.model.isDir(index_at_drop):
            destination_folder_path = os.path.dirname(self.model.filePath(index_at_drop))
        else:
            destination_folder_path = self.model.filePath(self.tree.rootIndex())
            if not os.path.isdir(destination_folder_path):
                destination_folder_path = os.path.dirname(destination_folder_path)

        if not destination_folder_path or not os.path.isdir(destination_folder_path):
            QMessageBox.warning(self, "드롭 오류", "유효한 대상 폴더를 찾을 수 없습니다.")
            event.ignore()
            return

        is_copy_action = (event.keyboardModifiers() == Qt.ControlModifier) or \
                         (event.dropAction() == Qt.CopyAction)
        if event.source() == self.tree :
            if event.dropAction() == Qt.MoveAction and (event.keyboardModifiers() == Qt.ControlModifier) :
                 is_copy_action = True
            elif event.dropAction() == Qt.CopyAction :
                 is_copy_action = True

        processed_at_least_one = False
        for url in mime_data.urls():
            src_path = url.toLocalFile()
            if not src_path or not os.path.exists(src_path):
                continue

            base_name = os.path.basename(src_path)
            if os.path.normpath(os.path.dirname(src_path)) == os.path.normpath(destination_folder_path) and \
               base_name == self.get_non_conflicting_name(destination_folder_path, base_name) and \
               not is_copy_action:
                continue

            dest_path_candidate = os.path.join(destination_folder_path, base_name)
            if is_copy_action or (not is_copy_action and os.path.exists(dest_path_candidate) and os.path.normpath(src_path) != os.path.normpath(dest_path_candidate)):
                dest_path = os.path.join(destination_folder_path, self.get_non_conflicting_name(destination_folder_path, base_name))
            else:
                dest_path = dest_path_candidate

            try:
                if is_copy_action:
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dest_path)
                    else:
                        shutil.copy2(src_path, dest_path)
                    self.push_undo({'type': 'copy', 'path': dest_path})
                else:
                    shutil.move(src_path, dest_path)
                    self.push_undo({'type': 'move', 'src': src_path, 'dst': dest_path})
                processed_at_least_one = True
            except Exception as e:
                QMessageBox.warning(self, "드롭 작업 오류", f"'{base_name}' 처리 중 오류: {e}")

        if processed_at_least_one:
            event.acceptProposedAction()
            self.refresh_current_view()
        else:
            event.ignore()

    def push_undo(self, action):
        self.undo_stack.append(action)
        if len(self.undo_stack) > self.MAX_UNDO:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            QMessageBox.information(self, "실행 취소", "되돌릴 작업이 없습니다.")
            return
        action = self.undo_stack.pop()
        try:
            if action['type'] == 'copy':
                if os.path.isdir(action['path']):
                    shutil.rmtree(action['path'])
                else:
                    os.remove(action['path'])
            elif action['type'] == 'move':
                shutil.move(action['dst'], action['src'])
            elif action['type'] == 'delete':
                if os.path.exists(action['backup']):
                    if os.path.isdir(action['backup']):
                        shutil.move(action['backup'], action['path'])
                    else:
                        shutil.move(action['backup'], action['path'])
                else:
                    QMessageBox.warning(self, "실행 취소 오류", "백업 파일이 존재하지 않아 복원할 수 없습니다.")
            elif action['type'] == 'rename':
                os.rename(action['new'], action['old'])
            elif action['type'] == 'mkdir':
                shutil.rmtree(action['path'])
            QMessageBox.information(self, "실행 취소", f"'{action['type']}' 작업이 취소되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "실행 취소 오류", f"실행 취소 실패: {e}")
        self.refresh_current_view()

    def keyPressEvent(self, event: QKeyEvent):
        if event.matches(QKeySequence.Undo): self.undo()
        elif event.matches(QKeySequence.Copy): self.copy_selected_items()
        elif event.matches(QKeySequence.Cut): self.cut_selected_items()
        elif event.matches(QKeySequence.Paste): self.paste_item()
        elif event.key() == Qt.Key_Delete: self.delete_items()
        else: super().keyPressEvent(event)

    # [수정] os.startfile을 subprocess.Popen으로 변경
    def on_double_click(self, index):
        if self.model.isDir(index):
            path = self.model.filePath(index)
            self.deferred_navigate(path)
        else:
            file_path = os.path.normpath(self.model.filePath(index))
            if Dispatch and QFileInfo(file_path).suffix().lower() == 'lnk':
                try:
                    shell = Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(file_path)
                    target_path = shortcut.TargetPath
                    if os.path.exists(target_path):
                        if os.path.isfile(target_path):
                            # os.startfile(target_path) -> subprocess.Popen으로 변경
                            subprocess.Popen(['start', '', target_path], shell=True, creationflags=subprocess.DETACHED_PROCESS)
                        else:
                            self.deferred_navigate(target_path)
                    else:
                        QMessageBox.warning(self, "바로가기 오류", "바로가기 대상이 존재하지 않습니다.")
                except Exception as e:
                    QMessageBox.warning(self, "바로가기 처리 오류", f"바로가기 파일 처리 중 오류 발생: {e}")
            elif os.path.isfile(file_path):
                try:
                    # os.startfile(file_path) -> subprocess.Popen으로 변경
                    subprocess.Popen(['start', '', file_path], shell=True, creationflags=subprocess.DETACHED_PROCESS)
                except Exception as e:
                    QMessageBox.warning(self, "파일 실행 오류", f"파일 실행 중 오류 발생: {e}")

    def go_back(self):
        if self.previous_paths:
            current_display_path = self.model.filePath(self.tree.rootIndex())
            self.forward_paths.append(current_display_path)
            prev_path = self.previous_paths.pop()
            index = self.model.index(prev_path)
            if index.isValid():
                self.tree.setRootIndex(index)
                self.update_path_input(index)

    def go_up(self):
        current_index = self.tree.rootIndex()
        current_path = self.model.filePath(current_index)
        parent_path = os.path.dirname(os.path.normpath(current_path))
        if parent_path and parent_path != current_path :
            self.previous_paths.append(current_path)
            self.forward_paths.clear()
            parent_index = self.model.index(parent_path)
            if parent_index.isValid():
                self.tree.setRootIndex(parent_index)
                self.update_path_input(parent_index)

    def go_forward(self):
        if self.forward_paths:
            current_display_path = self.model.filePath(self.tree.rootIndex())
            self.previous_paths.append(current_display_path)
            next_path = self.forward_paths.pop()
            index = self.model.index(next_path)
            if index.isValid():
                self.tree.setRootIndex(index)
                self.update_path_input(index)

    def delete_explorer(self):
        main_window = self.window()
        if isinstance(main_window, MainWindow):
             main_window.request_panel_removal(self)
        else:
            self.setParent(None)
            self.deleteLater()

    def on_path_input_change(self):
        new_path = self.path_input.text().strip()
        if os.path.isdir(new_path):
            current_path = self.model.filePath(self.tree.rootIndex())
            if os.path.normpath(current_path) != os.path.normpath(new_path):
                self.previous_paths.append(current_path)
                self.forward_paths.clear()
            new_index = self.model.index(new_path)
            if new_index.isValid():
                self.tree.setRootIndex(new_index)
                self.update_path_input(new_index)
            else:
                QMessageBox.warning(self, "경로 오류", "유효하지 않은 경로입니다.")
                self.update_path_input(self.tree.rootIndex())
        else:
            QMessageBox.warning(self, "경로 오류", "존재하지 않거나 폴더가 아닌 경로입니다.")
            self.update_path_input(self.tree.rootIndex())

    def update_path_input(self, index):
        path_from_model = self.model.filePath(index)
        windows_style_path = os.path.normpath(path_from_model)

        if hasattr(self, 'path_input'):
            self.path_input.setText(windows_style_path)

        if windows_style_path and os.path.exists(windows_style_path) and os.path.isdir(windows_style_path):
            last_folder = os.path.basename(windows_style_path)
            if not last_folder and len(windows_style_path) > 0 and (windows_style_path.endswith(':') or windows_style_path.endswith(':\\')):
                last_folder = windows_style_path
            if hasattr(self, 'folder_label'):
                self.folder_label.setText(last_folder if last_folder else "<루트>")
        else:
            current_root_idx = self.tree.rootIndex()
            current_root_path_from_model = self.model.filePath(current_root_idx)
            current_root_windows_path = os.path.normpath(current_root_path_from_model)

            if current_root_windows_path and os.path.exists(current_root_windows_path) and os.path.isdir(current_root_windows_path):
                if hasattr(self, 'path_input'): self.path_input.setText(current_root_windows_path)
                if hasattr(self, 'folder_label'): self.folder_label.setText(os.path.basename(current_root_windows_path) or current_root_windows_path)
            else:
                home_path_from_qt = QDir.homePath()
                home_windows_path = os.path.normpath(home_path_from_qt)

                if hasattr(self, 'path_input'): self.path_input.setText(home_windows_path)
                if hasattr(self, 'folder_label'): self.folder_label.setText(os.path.basename(home_windows_path))

                home_index = self.model.index(home_path_from_qt)
                if home_index.isValid():
                    self.tree.setRootIndex(home_index)

    def add_path_to_new_explorer(self, path):
        target_path = ""
        if os.path.isdir(path):
            target_path = path
        else:
            target_path = os.path.dirname(path)

        if target_path:
            self.request_new_panel.emit(target_path)

    def show_context_menu(self, pos):
        try:
            viewport_pos = self.tree.viewport().mapToGlobal(pos)
            index_at_pos = self.tree.indexAt(pos)
            menu = QMenu(self)

            current_tree_root_path = self.model.filePath(self.tree.rootIndex())
            if not current_tree_root_path or not os.path.isdir(current_tree_root_path):
                current_tree_root_path = QDir.homePath()
                if not os.path.isdir(current_tree_root_path):
                    current_tree_root_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)

            target_dir_path_for_paste_newfolder = ""
            target_item_path_for_open_props = ""
            target_item_index_for_open_props = QModelIndex()

            if index_at_pos.isValid():
                path_at_clicked_item = self.model.filePath(index_at_pos)
                if path_at_clicked_item and os.path.exists(path_at_clicked_item):
                    target_item_index_for_open_props = index_at_pos
                    target_item_path_for_open_props = path_at_clicked_item
                    if self.model.isDir(index_at_pos):
                        target_dir_path_for_paste_newfolder = path_at_clicked_item
                    else:
                        target_dir_path_for_paste_newfolder = os.path.dirname(path_at_clicked_item)
                else:
                    target_dir_path_for_paste_newfolder = current_tree_root_path
                    target_item_index_for_open_props = self.tree.rootIndex()
                    target_item_path_for_open_props = current_tree_root_path
            else:
                target_dir_path_for_paste_newfolder = current_tree_root_path
                target_item_index_for_open_props = self.tree.rootIndex()
                target_item_path_for_open_props = current_tree_root_path

            if not target_dir_path_for_paste_newfolder or not os.path.isdir(target_dir_path_for_paste_newfolder):
                QMessageBox.warning(self, "경고", "작업 대상 폴더를 결정할 수 없습니다.")
                return

            if target_item_index_for_open_props.isValid() and target_item_path_for_open_props and os.path.exists(target_item_path_for_open_props) :
                open_action = QAction("열기(&O)", self)
                open_action.triggered.connect(lambda checked, idx=QModelIndex(target_item_index_for_open_props): self.on_double_click(idx))
                menu.addAction(open_action)

            if target_item_path_for_open_props and os.path.exists(target_item_path_for_open_props):
                open_in_explorer_action = QAction("새 창에서 열기(&E)", self)
                open_in_explorer_action.triggered.connect(lambda checked, p=str(target_item_path_for_open_props): self.open_path_in_system_explorer(p))
                menu.addAction(open_in_explorer_action)

                add_to_explorer_action = QAction("탐색기에 추가", self)
                add_to_explorer_action.triggered.connect(lambda checked, p=str(target_item_path_for_open_props): self.add_path_to_new_explorer(p))
                menu.addAction(add_to_explorer_action)

            menu.addSeparator()

            selected_indexes = self.tree.selectedIndexes()
            has_valid_selection = any(idx.isValid() and idx.column() == 0 for idx in selected_indexes)

            copy_action = QAction("복사", self)
            copy_action.triggered.connect(self.copy_selected_items)
            copy_action.setEnabled(has_valid_selection)
            menu.addAction(copy_action)

            cut_action = QAction("잘라내기", self)
            cut_action.triggered.connect(self.cut_selected_items)
            cut_action.setEnabled(has_valid_selection)
            menu.addAction(cut_action)

            paste_action = QAction("붙여넣기", self)
            paste_action.triggered.connect(lambda checked, dest=str(target_dir_path_for_paste_newfolder): self.paste_item_to_path(dest))
            paste_action.setEnabled(
                bool(QApplication.clipboard().mimeData().hasUrls() or \
                     (ExplorerPanel.copied_item and len(ExplorerPanel.copied_item) > 0) or \
                     (ExplorerPanel.cut_item and len(ExplorerPanel.cut_item) > 0))
            )
            menu.addAction(paste_action)
            menu.addSeparator()

            delete_action = QAction("삭제", self)
            delete_action.triggered.connect(self.delete_items)
            delete_action.setEnabled(has_valid_selection)
            menu.addAction(delete_action)
            menu.addSeparator()

            new_folder_action = QAction("새 폴더 만들기(&N)", self)
            new_folder_action.triggered.connect(lambda checked, p=str(target_dir_path_for_paste_newfolder): self.create_new_folder_in_path(p))
            menu.addAction(new_folder_action)

            first_selected_and_valid_for_rename = None
            if index_at_pos.isValid() and index_at_pos.column() == 0 and index_at_pos != self.tree.rootIndex():
                first_selected_and_valid_for_rename = index_at_pos
            elif has_valid_selection:
                for idx_sel in selected_indexes:
                    if idx_sel.isValid() and idx_sel.column() == 0 and idx_sel != self.tree.rootIndex():
                        first_selected_and_valid_for_rename = idx_sel
                        break

            if first_selected_and_valid_for_rename:
                rename_action = QAction("이름 바꾸기", self)
                rename_action.triggered.connect(lambda checked, idx_to_rename=QModelIndex(first_selected_and_valid_for_rename): self.rename_item(idx_to_rename))
                menu.addAction(rename_action)

            menu.addSeparator()

            if target_item_path_for_open_props and os.path.exists(target_item_path_for_open_props):
                prop_action = QAction("속성(&R)", self)
                prop_action.triggered.connect(lambda checked, p=str(target_item_path_for_open_props): self.show_properties_for_path(p))
                menu.addAction(prop_action)
            menu.exec_(viewport_pos)

        except Exception as e:
            import traceback
            print(f"Error in show_context_menu: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "컨텍스트 메뉴 오류", f"메뉴를 표시하는 중 오류가 발생했습니다:\n{e}")

    # [수정] os.startfile과 subprocess.run을 subprocess.Popen으로 변경
    def open_path_in_system_explorer(self, path):
        if os.path.exists(path):
            norm_path = os.path.normpath(path)
            try:
                if os.path.isdir(norm_path):
                    # os.startfile(norm_path) -> subprocess.Popen으로 변경
                    subprocess.Popen(['start', '', norm_path], shell=True, creationflags=subprocess.DETACHED_PROCESS)
                else:
                    # subprocess.run(...) -> subprocess.Popen으로 변경
                    subprocess.Popen(['explorer', '/select,', norm_path], creationflags=subprocess.DETACHED_PROCESS)
            except Exception as e:
                QMessageBox.warning(self, "탐색기 열기 오류", f"시스템 탐색기 실행 중 오류: {e}")
        else:
            QMessageBox.warning(self, "오류", f"경로를 찾을 수 없습니다: {path}")

    def show_properties_for_path(self, path):
        if os.path.exists(path): show_windows_properties(path)
        else: QMessageBox.warning(self, "오류", f"경로를 찾을 수 없습니다: {path}")

    def eventFilter(self, obj, event):
        if obj == self.tree and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                selected = self.tree.selectedIndexes()
                if selected:
                    first_selected_col0 = None
                    for idx_sel in selected:
                        if idx_sel.column() == 0:
                            first_selected_col0 = idx_sel
                            break
                    if first_selected_col0:
                        self.on_double_click(first_selected_col0)
                        return True
        return super().eventFilter(obj, event)

    def rename_item(self, index):
        if not index.isValid() or index.column() != 0:
            if index.isValid(): index = index.sibling(index.row(), 0)
            else: return

        old_path_from_model = self.model.filePath(index)
        old_path = os.path.normpath(old_path_from_model)
        old_name = os.path.basename(old_path)
        dir_path = os.path.dirname(old_path)

        new_name, ok = QInputDialog.getText(self, "이름 바꾸기", "새 이름:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(dir_path, new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "이름 바꾸기", "이미 같은 이름의 파일이나 폴더가 존재합니다.")
                return
            try:
                os.rename(old_path, new_path)
                self.push_undo({'type': 'rename', 'old': old_path, 'new': new_path})

                def select_renamed_item():
                    new_item_index = self.model.index(new_path)
                    if new_item_index.isValid():
                        self.tree.setCurrentIndex(new_item_index)
                        self.tree.scrollTo(new_item_index, QAbstractItemView.PositionAtCenter)
                QTimer.singleShot(100, select_renamed_item)
            except Exception as e: QMessageBox.critical(self, "이름 바꾸기 오류", str(e))

    def create_new_folder_in_path(self, parent_path_str):
        if not os.path.isdir(parent_path_str):
            QMessageBox.warning(self, "새 폴더 오류", "폴더를 생성할 유효한 상위 경로가 아닙니다.")
            return

        base_name = "새 폴더"
        new_folder_path = os.path.join(parent_path_str, base_name)
        counter = 1
        while os.path.exists(new_folder_path):
            new_folder_path = os.path.join(parent_path_str, f"{base_name} ({counter})")
            counter += 1

        try:
            os.mkdir(new_folder_path)
            self.push_undo({'type': 'mkdir', 'path': new_folder_path})

            def _select_and_edit_new_folder():
                new_folder_index = self.model.index(new_folder_path)
                if new_folder_index.isValid():
                    parent_of_new_folder_idx = self.model.parent(new_folder_index)
                    current_tree_root_idx = self.tree.rootIndex()
                    if parent_of_new_folder_idx == current_tree_root_idx: pass
                    elif self.model.filePath(parent_of_new_folder_idx).startswith(self.model.filePath(current_tree_root_idx)):
                         self.tree.expand(parent_of_new_folder_idx)

                    self.tree.setCurrentIndex(new_folder_index)
                    self.tree.scrollTo(new_folder_index)
                    self.tree.edit(new_folder_index)
                else: print(f"새 폴더 인덱스 못찾음: {new_folder_path}")
            QTimer.singleShot(250, _select_and_edit_new_folder)
        except Exception as e:
            QMessageBox.critical(self, "새 폴더 생성 오류", str(e))
            print(f"새 폴더 생성 오류: {e}")

    def create_new_folder(self, index_for_context=None):
        parent_path_str = ""
        if index_for_context and index_for_context.isValid():
            path_clicked = self.model.filePath(index_for_context)
            if self.model.isDir(index_for_context): parent_path_str = path_clicked
            else: parent_path_str = os.path.dirname(path_clicked)
        else: parent_path_str = self.model.filePath(self.tree.rootIndex())

        if not parent_path_str or not os.path.isdir(parent_path_str):
            parent_path_str = QDir.currentPath()
        self.create_new_folder_in_path(parent_path_str)

    def copy_to_clipboard(self, file_paths, cut=False):
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(path) for path in file_paths]
        mime_data.setUrls(urls)

        if cut: mime_data.setData('application/x-qt-windows-mime;value="PreferredDropEffect"', b'\x02\x00\x00\x00')
        else: mime_data.setData('application/x-qt-windows-mime;value="PreferredDropEffect"', b'\x05\x00\x00\x00')
        QApplication.clipboard().setMimeData(mime_data)

    def copy_selected_items(self):
        selected = self.tree.selectedIndexes()
        if not selected: return
        paths_to_copy = sorted(list(set(self.model.filePath(idx) for idx in selected if idx.column() == 0)))
        if paths_to_copy:
            ExplorerPanel.copied_item = paths_to_copy
            ExplorerPanel.cut_item = None
            self.copy_to_clipboard(paths_to_copy, cut=False)
            main_window = self.window()
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(f"{len(paths_to_copy)}개 항목 복사됨", 2000)

    def cut_selected_items(self):
        selected = self.tree.selectedIndexes()
        if not selected: return
        paths_to_cut = sorted(list(set(self.model.filePath(idx) for idx in selected if idx.column() == 0)))
        if paths_to_cut:
            ExplorerPanel.cut_item = paths_to_cut
            ExplorerPanel.copied_item = None
            self.copy_to_clipboard(paths_to_cut, cut=True)
            main_window = self.window()
            if hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(f"{len(paths_to_cut)}개 항목 잘라내기됨", 2000)

    def get_non_conflicting_name(self, dest_dir, name):
        base, ext = os.path.splitext(name)
        counter = 1
        new_name = name
        while os.path.exists(os.path.join(dest_dir, new_name)):
            new_name = f"{base} ({counter}){ext}"
            counter += 1
        return new_name

    def paste_item_to_path(self, destination_folder):
        pasted_something = False
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasUrls():
            drop_effect_data = mime_data.data('application/x-qt-windows-mime;value="PreferredDropEffect"')
            is_cut_from_clipboard = drop_effect_data == b'\x02\x00\x00\x00'
            src_urls = mime_data.urls()
            sources_to_paste = [url.toLocalFile() for url in src_urls]

            for src_path in sources_to_paste:
                if not os.path.exists(src_path): continue
                name = os.path.basename(os.path.normpath(src_path))
                new_name = self.get_non_conflicting_name(destination_folder, name)
                dest_path = os.path.join(destination_folder, new_name)
                try:
                    if is_cut_from_clipboard:
                        shutil.move(src_path, dest_path)
                        if ExplorerPanel.cut_item and src_path in ExplorerPanel.cut_item:
                             self.push_undo({'type': 'move', 'src': src_path, 'dst': dest_path})
                    else:
                        if os.path.isdir(src_path): shutil.copytree(src_path, dest_path)
                        else: shutil.copy2(src_path, dest_path)
                        self.push_undo({'type': 'copy', 'path': dest_path})
                    pasted_something = True
                except Exception as e: QMessageBox.warning(self, "붙여넣기 오류", f"클립보드 항목 '{name}' 처리 실패: {e}")

            if pasted_something:
                if is_cut_from_clipboard: ExplorerPanel.cut_item = None
                self.refresh_current_view()
                return

        source_items_list = None
        operation_is_move = False

        if ExplorerPanel.copied_item: source_items_list = ExplorerPanel.copied_item
        elif ExplorerPanel.cut_item:
            source_items_list = ExplorerPanel.cut_item
            operation_is_move = True

        if not source_items_list:
            if not pasted_something: QMessageBox.information(self, "붙여넣기", "붙여넣기 할 항목이 없습니다.")
            return

        if not isinstance(source_items_list, list): source_items_list = [source_items_list]

        for src_path in source_items_list:
            if not os.path.exists(src_path): continue
            name = os.path.basename(os.path.normpath(src_path))
            new_name = self.get_non_conflicting_name(destination_folder, name)
            dest_path = os.path.join(destination_folder, new_name)
            try:
                if operation_is_move:
                    shutil.move(src_path, dest_path)
                    self.push_undo({'type': 'move', 'src': src_path, 'dst': dest_path})
                else:
                    if os.path.isdir(src_path): shutil.copytree(src_path, dest_path)
                    else: shutil.copy2(src_path, dest_path)
                    self.push_undo({'type': 'copy', 'path': dest_path})
                pasted_something = True
            except Exception as e: QMessageBox.warning(self, "붙여넣기 오류", f"내부 항목 '{name}' 처리 실패: {e}")

        if operation_is_move and pasted_something: ExplorerPanel.cut_item = None
        if pasted_something: self.refresh_current_view()

    def paste_item(self):
        selected_indexes = self.tree.selectedIndexes()
        destination_path = ""

        if selected_indexes:
            first_selected_idx = selected_indexes[0]
            if self.model.isDir(first_selected_idx): destination_path = self.model.filePath(first_selected_idx)
            else: destination_path = os.path.dirname(self.model.filePath(first_selected_idx))
        else: destination_path = self.model.filePath(self.tree.rootIndex())

        if not os.path.isdir(destination_path):
            destination_path = self.model.filePath(self.tree.rootIndex())
            if not os.path.isdir(destination_path): destination_path = QDir.rootPath()
        self.paste_item_to_path(destination_path)

    def delete_items(self):
        selected_indexes = self.tree.selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "삭제", "삭제할 항목을 선택하세요.")
            return

        paths_to_delete = sorted(list(set(self.model.filePath(idx) for idx in selected_indexes if idx.column() == 0)))
        if not paths_to_delete: return

        reply = QMessageBox.question(self, "삭제 확인",
                                     f"{len(paths_to_delete)}개 항목을 삭제하시겠습니까?\n(이 작업은 '실행 취소'로 복구 가능합니다)",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: return

        self.tree.setUpdatesEnabled(False)
        current_root_path_norm = os.path.normpath(self.model.filePath(self.tree.rootIndex()))
        root_itself_or_direct_child_deleted = False

        for path in paths_to_delete:
            if not os.path.exists(path): continue
            path_norm = os.path.normpath(path)
            if path_norm == current_root_path_norm or os.path.dirname(path_norm) == current_root_path_norm:
                root_itself_or_direct_child_deleted = True
            try:
                temp_dir = os.path.join(tempfile.gettempdir(), "explorerpanel_undo")
                os.makedirs(temp_dir, exist_ok=True)
                backup_name = os.path.basename(path) + "_" + str(uuid.uuid4().hex[:8])
                backup_path = os.path.join(temp_dir, backup_name)
                if os.path.isdir(path):
                    shutil.copytree(path, backup_path)
                    shutil.rmtree(path)
                else:
                    shutil.copy2(path, backup_path)
                    os.remove(path)
                self.push_undo({'type': 'delete', 'path': path, 'backup': backup_path})
            except Exception as e:
                QMessageBox.warning(self, "삭제 오류", f"'{os.path.basename(path)}' 삭제 실패: {e}")
                print(f"Error deleting {path}: {e}")

        self.tree.setUpdatesEnabled(True)

        if root_itself_or_direct_child_deleted and not os.path.exists(current_root_path_norm) :
            parent_of_old_root = os.path.dirname(current_root_path_norm)
            if os.path.exists(parent_of_old_root) and parent_of_old_root != current_root_path_norm:
                new_root_index = self.model.index(parent_of_old_root)
                if new_root_index.isValid():
                    self.tree.setRootIndex(new_root_index)
                    self.update_path_input(new_root_index)
            else:
                default_path_index = self.model.index('')
                self.tree.setRootIndex(default_path_index)
                self.update_path_input(default_path_index)
        else: self.refresh_current_view()

    def on_directory_loaded(self, path):
        if self.pending_navigation_path and os.path.normpath(path) == os.path.normpath(self.pending_navigation_path):
            target_index = self.model.index(self.pending_navigation_path)
            if target_index.isValid():
                current_path_norm = os.path.normpath(self.model.filePath(self.tree.rootIndex()))
                if current_path_norm != os.path.normpath(self.pending_navigation_path):
                    self.previous_paths.append(self.model.filePath(self.tree.rootIndex()))
                    self.forward_paths.clear()
                self.tree.setRootIndex(target_index)
                self.update_path_input(target_index)
            self.pending_navigation_path = None

    def deferred_navigate(self, new_path):
        self.pending_navigation_path = new_path
        self.model.index(new_path)

    def refresh_current_view(self):
        pass
# --- ExplorerPanel 클래스 끝 ---

# FlowLayout 클래스
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hspacing=-1, vspacing=-1):
        super(FlowLayout, self).__init__(parent)
        if parent is not None: self.setContentsMargins(margin, margin, margin, margin)
        self._hspacing = hspacing
        self._vspacing = vspacing
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)

    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList.pop(index)
        return None

    def expandingDirections(self): return Qt.Orientations(Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width):
        height = self._doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList: size = size.expandedTo(item.minimumSize())
        mrg = self.contentsMargins()
        size += QSize(mrg.left() + mrg.right(), mrg.top() + mrg.bottom())
        return size

    def horizontalSpacing(self):
        if self._hspacing >= 0: return self._hspacing
        else: return self.smartSpacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vspacing >= 0: return self._vspacing
        else: return self.smartSpacing(QStyle.PM_LayoutVerticalSpacing)

    def smartSpacing(self, pm):
        parent = self.parent()
        if parent is None: return -1
        elif parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
        else: return parent.spacing()

    def _doLayout(self, rect, testOnly):
        m = self.contentsMargins()
        effectiveRect = rect.adjusted(+m.left(), +m.top(), -m.right(), -m.bottom())
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1: spaceX = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1: spaceY = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - effectiveRect.y()

# CustomColorPickerDialog 클래스
class CustomColorPickerDialog(QDialog):
    def __init__(self, predefined_colors, current_color_hex=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("색상 선택")
        self.selected_color_hex = current_color_hex
        self.predefined_colors = predefined_colors

        layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        layout.addLayout(self.grid_layout)
        self.color_buttons = {}
        row, col = 0, 0
        colors_per_row = 5

        for color_name, color_hex in self.predefined_colors.items():
            btn = QPushButton("")
            btn.setToolTip(f"{color_name} ({color_hex})")
            btn.setStyleSheet(f"background-color: {color_hex}; border: 1px solid gray;")
            btn.clicked.connect(functools.partial(self.color_button_clicked, color_hex, color_name))
            if color_hex == self.selected_color_hex:
                btn.setStyleSheet(f"background-color: {color_hex}; border: 2px solid blue;")
            self.grid_layout.addWidget(btn, row, col)
            self.color_buttons[color_hex] = btn
            col += 1
            if col >= colors_per_row:
                col = 0
                row += 1

    def get_text_color_for_background(self, bg_hex_color):
        try:
            color = QColor(bg_hex_color)
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            return "black" if brightness > 128 else "white"
        except: return "black"

    def color_button_clicked(self, color_hex, color_name):
        if self.selected_color_hex and self.selected_color_hex in self.color_buttons:
            prev_btn_hex = self.selected_color_hex
            prev_btn = self.color_buttons[prev_btn_hex]
            prev_btn.setStyleSheet(f"background-color: {prev_btn_hex}; color: {self.get_text_color_for_background(prev_btn_hex)}; border: 1px solid gray;")

        self.selected_color_hex = color_hex
        current_btn = self.color_buttons[self.selected_color_hex]
        current_btn.setStyleSheet(f"background-color: {self.selected_color_hex}; color: {self.get_text_color_for_background(self.selected_color_hex)}; border: 2px solid blue;")
        self.accept()

    def get_selected_color(self): return self.selected_color_hex


# --- [새로운 클래스] 경로 즐겨찾기 추가/수정을 위한 다이얼로그 ---
class PathFavoriteDialog(QDialog):
    def __init__(self, parent=None, name="", path=""):
        super().__init__(parent)
        self.setWindowTitle("경로 즐겨찾기 설정")

        self.layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("버튼 이름:"), 0, 0)
        self.name_input = QLineEdit(name)
        form_layout.addWidget(self.name_input, 0, 1)

        form_layout.addWidget(QLabel("경로:"), 1, 0)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(path)
        path_layout.addWidget(self.path_input)

        browse_button = QPushButton("찾아보기...")
        browse_button.clicked.connect(self.browse_folder)
        path_layout.addWidget(browse_button)

        form_layout.addLayout(path_layout, 1, 1)

        self.layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)

    def browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "폴더 선택", self.path_input.text())
        if directory:
            self.path_input.setText(os.path.normpath(directory))

    def get_data(self):
        return self.name_input.text().strip(), self.path_input.text().strip()


# MainWindow 클래스
class MainWindow(QMainWindow):
    ROW_MODE = 0
    COL_MODE = 1
    FAVORITE_COUNT = 20
    DEFAULT_LINE_CAPACITIES = [3]
    SESSION_CONFIG_FILENAME = "default_session.json"
    FAVORITES_CONFIG_FILENAME = "favorites_dict.json"
    PATH_FAVORITES_CONFIG_FILENAME = "path_favorites.json"
    DEFAULT_PATH_FAV_COLOR = "#C1D6EE" # 경로추가 기본색상

    def __init__(self):
        super().__init__()
        self.setWindowTitle("다중 탐색기 - 최종")

        self.panels_in_logical_order = []
        self.current_layout_mode = MainWindow.ROW_MODE
        self.line_capacities = list(self.DEFAULT_LINE_CAPACITIES)
        self.panel_grid_structure = self._calculate_panel_grid_structure()
        self.favorite_layouts = {}
        self.path_favorites = {}
        self.last_splitter_states = None

        self.predefined_colors = {
            "연노랑": "#FFFACD", "연연두": "#caf3be", "연하늘": "#bfe5f7", "연핑크": "#fddff5", "연보라": "#dec9fa",
            "노랑": "#ffee00", "연두": "#79fa00", "하늘": "#2ad4ff", "핑크": "#ffb3e8", "보라": "#c497ff",
            "주황": "#FFBB00", "초록": "#32E09D", "파랑": "#84a1ff", "빨강": "#ff7070", "회색": "white",
        }

        _central_widget = QWidget()
        self.setCentralWidget(_central_widget)
        self.overall_layout = QVBoxLayout(_central_widget)
        self.top_controls_widget = QWidget()
        self.overall_layout.addWidget(self.top_controls_widget)
        self.setup_top_controls()

        self.content_area_host = QWidget()
        self.content_area_host_layout = QVBoxLayout()
        self.content_area_host.setLayout(self.content_area_host_layout)
        self.overall_layout.addWidget(self.content_area_host, 1)

        self.resize(1200, 800)
        self.setup_status_bar()

        self.load_favorites_config()
        self.update_favorite_buttons_ui()
        self.load_path_favorites_config()
        self.update_path_favorite_buttons_ui()

        session_layout_loaded = self.load_layout_from_file(
            self.get_app_config_path(self.SESSION_CONFIG_FILENAME),
            is_session_load_for_panels_only=True
        )

        if not session_layout_loaded:
            if not self.panels_in_logical_order: self.add_explorer_panel()
        elif self.panels_in_logical_order: self.rebuild_ui_from_structure()

    def handle_favorite_click(self, fav_name):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == (Qt.ControlModifier | Qt.ShiftModifier): self.delete_favorite_slot(fav_name)
        elif modifiers == Qt.ShiftModifier:
            fav_data = self.favorite_layouts.get(fav_name, {})
            existing_filepath = fav_data.get("path") if isinstance(fav_data, dict) else None
            self.save_current_layout_to_favorite_slot(fav_name, existing_filepath)
        else: self.load_layout_from_favorite_slot(fav_name)

    def setup_top_controls(self):
        top_v_layout = QVBoxLayout(self.top_controls_widget)
        top_v_layout.setContentsMargins(5, 5, 5, 5)
        top_v_layout.setSpacing(5)

        # 행 1
        row1_layout = QHBoxLayout()
        self.add_explorer_button = QPushButton("탐색기 추가")
        self.add_explorer_button.clicked.connect(self.add_explorer_panel)
        row1_layout.addWidget(self.add_explorer_button)

        self.add_path_fav_btn = QPushButton("♡")
        self.add_path_fav_btn.setToolTip("경로 즐겨찾기 추가")
        self.add_path_fav_btn.setFixedWidth(30)
        self.add_path_fav_btn.clicked.connect(self.add_new_path_favorite)
        row1_layout.addWidget(self.add_path_fav_btn)

        self.path_favorites_container = QWidget()
        self.path_favorites_flow_layout = FlowLayout(self.path_favorites_container, margin=0, hspacing=5, vspacing=5)
        row1_layout.addWidget(self.path_favorites_container, 1)

        row1_layout.addSpacerItem(QSpacerItem(10, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.toggle_layout_button = QPushButton("토글")
        self.toggle_layout_button.clicked.connect(self.toggle_overall_layout_mode)
        row1_layout.addWidget(self.toggle_layout_button)

        self.line_capacity_button = QPushButton(f"최대: {','.join(map(str, self.line_capacities))}")
        self.line_capacity_button.setToolTip("각 단/열의 패널수를 콤마(,)로 구분하여 입력하세요.\n예: 3,2,3")
        self.line_capacity_button.clicked.connect(self.set_line_capacities_config)
        row1_layout.addWidget(self.line_capacity_button)

        self.reset_path_button = QPushButton("경로 초기화")
        self.reset_path_button.setToolTip("모든 경로 즐겨찾기를 초기화합니다.")
        self.reset_path_button.clicked.connect(self.reset_path_favorites_dialog)
        row1_layout.addWidget(self.reset_path_button)

        top_v_layout.addLayout(row1_layout)

        # 행 2
        row2_layout = QHBoxLayout()
        self.load_default_button = QPushButton("시작창")
        self.load_default_button.setToolTip("저장된 시작창 레이아웃을 불러옵니다.")
        self.load_default_button.clicked.connect(self.load_default_session)
        row2_layout.addWidget(self.load_default_button)

        self.add_layout_fav_btn = QPushButton("♡")
        self.add_layout_fav_btn.setToolTip("현재 레이아웃을 새 즐겨찾기로 추가")
        self.add_layout_fav_btn.setFixedWidth(30)
        self.add_layout_fav_btn.clicked.connect(self.add_new_favorite_slot)
        row2_layout.addWidget(self.add_layout_fav_btn)

        self.favorites_buttons_container = QWidget()
        self.favorite_buttons_flow_layout = FlowLayout(self.favorites_buttons_container, margin=0, hspacing=5, vspacing=5)
        row2_layout.addWidget(self.favorites_buttons_container, 1)

        row2_layout.addSpacerItem(QSpacerItem(10, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.reset_layout_button = QPushButton("레이아웃 초기화")
        self.reset_layout_button.setToolTip("모든 레이아웃 즐겨찾기를 초기화합니다.")
        self.reset_layout_button.clicked.connect(self.reset_layouts_dialog)
        row2_layout.addWidget(self.reset_layout_button)

        self.save_as_default_button = QPushButton("시작창으로 저장")
        self.save_as_default_button.setToolTip("현재 레이아웃을 프로그램 시작 시 기본값으로 저장합니다.")
        self.save_as_default_button.clicked.connect(self.save_current_state_as_default)
        row2_layout.addWidget(self.save_as_default_button)
        top_v_layout.addLayout(row2_layout)

    def update_favorite_buttons_ui(self):
        while self.favorite_buttons_flow_layout.count():
            item = self.favorite_buttons_flow_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        for fav_name in sorted(self.favorite_layouts.keys()):
            fav_data = self.favorite_layouts[fav_name]
            filepath = fav_data.get("path", "")
            button_color = fav_data.get("color", "white")
            btn_text = fav_name if len(fav_name) < 10 else fav_name[:7] + "..."
            fav_button = QPushButton(btn_text)
            current_style = f"background-color: {button_color}; padding: 2px 5px; border: 1px solid gray;"
            tooltip_text = f"'{fav_name}' 레이아웃 불러오기\n(Shift+클릭: 덮어쓰기, 우클릭: 메뉴)"
            if not filepath or not os.path.exists(filepath):
                fav_button.setStyleSheet(current_style + "color: gray; font-style: italic;")
            else: fav_button.setStyleSheet(current_style + "font-weight: bold;")
            fav_button.setToolTip(tooltip_text)
            fav_button.clicked.connect(functools.partial(self.handle_favorite_click, fav_name))
            fav_button.setContextMenuPolicy(Qt.CustomContextMenu)
            fav_button.customContextMenuRequested.connect(functools.partial(self.show_favorite_button_context_menu, fav_name, fav_button))
            self.favorite_buttons_flow_layout.addWidget(fav_button)

        if hasattr(self, 'add_layout_fav_btn'):
            self.add_layout_fav_btn.setVisible(len(self.favorite_layouts) < self.FAVORITE_COUNT)
        self.favorite_buttons_flow_layout.invalidate()
        self.favorites_buttons_container.updateGeometry()

    def add_explorer_panel_with_path(self, path):
        self.add_explorer_panel(path)
        self.statusBar().showMessage(f"'{path}' 경로로 탐색기를 추가했습니다.", 2000)

    def update_path_favorite_buttons_ui(self):
        while self.path_favorites_flow_layout.count():
            item = self.path_favorites_flow_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        for name in sorted(self.path_favorites.keys()):
            fav_data = self.path_favorites[name]
            path = fav_data.get("path", "")
            color = fav_data.get("color", self.DEFAULT_PATH_FAV_COLOR)

            btn = QPushButton(name)
            btn.setStyleSheet(f"background-color: {color}; padding: 2px 5px; border: 1px solid gray;")
            btn.setToolTip(f"'{path}' 경로의 탐색기 추가\n(우클릭으로 메뉴 열기)")
            btn.clicked.connect(lambda checked, p=path: self.add_explorer_panel_with_path(p))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(functools.partial(self.show_path_favorite_button_context_menu, name, btn))
            self.path_favorites_flow_layout.addWidget(btn)

        self.path_favorites_flow_layout.invalidate()
        self.path_favorites_container.updateGeometry()

    def add_new_path_favorite(self):
        dialog = PathFavoriteDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, path = dialog.get_data()
            if not name or not path:
                QMessageBox.warning(self, "입력 오류", "버튼 이름과 경로를 모두 입력해야 합니다.")
                return
            if not os.path.isdir(path):
                QMessageBox.warning(self, "경로 오류", "유효한 폴더 경로가 아닙니다.")
                return
            if name in self.path_favorites:
                QMessageBox.warning(self, "이름 중복", "이미 사용 중인 즐겨찾기 이름입니다.")
                return

            self.path_favorites[name] = {"path": path, "color": self.DEFAULT_PATH_FAV_COLOR}
            self.save_path_favorites_config()
            self.update_path_favorite_buttons_ui()
            self.statusBar().showMessage(f"경로 '{name}'이(가) 즐겨찾기에 추가되었습니다.", 2000)

    def edit_path_favorite(self, old_name):
        fav_data = self.path_favorites.get(old_name)
        if not fav_data: return

        path = fav_data.get("path", "")
        current_color = fav_data.get("color", self.DEFAULT_PATH_FAV_COLOR)

        dialog = PathFavoriteDialog(self, name=old_name, path=path)
        if dialog.exec_() == QDialog.Accepted:
            new_name, new_path = dialog.get_data()
            if not new_name or not new_path:
                QMessageBox.warning(self, "입력 오류", "버튼 이름과 경로를 모두 입력해야 합니다.")
                return
            if not os.path.isdir(new_path):
                QMessageBox.warning(self, "경로 오류", "유효한 폴더 경로가 아닙니다.")
                return
            if new_name != old_name and new_name in self.path_favorites:
                QMessageBox.warning(self, "이름 중복", "이미 사용 중인 즐겨찾기 이름입니다.")
                return

            if old_name in self.path_favorites:
                del self.path_favorites[old_name]

            self.path_favorites[new_name] = {"path": new_path, "color": current_color}
            self.save_path_favorites_config()
            self.update_path_favorite_buttons_ui()
            self.statusBar().showMessage(f"경로 즐겨찾기 '{new_name}'이(가) 수정되었습니다.", 2000)

    def delete_path_favorite(self, name):
        reply = QMessageBox.question(self, "삭제 확인", f"'{name}' 경로 즐겨찾기를 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if name in self.path_favorites:
                del self.path_favorites[name]
                self.save_path_favorites_config()
                self.update_path_favorite_buttons_ui()
                self.statusBar().showMessage(f"'{name}' 즐겨찾기가 삭제되었습니다.", 2000)

    def show_path_favorite_button_context_menu(self, fav_name, button_widget, pos):
        menu = QMenu(self)
        edit_action = menu.addAction("수정")
        delete_action = menu.addAction("삭제")
        menu.addSeparator()
        change_color_action = menu.addAction("버튼 색상 변경...")

        action = menu.exec_(button_widget.mapToGlobal(pos))

        if action == edit_action:
            self.edit_path_favorite(fav_name)
        elif action == delete_action:
            self.delete_path_favorite(fav_name)
        elif action == change_color_action:
            QTimer.singleShot(0, lambda: self.change_path_favorite_button_color(fav_name, button_widget))

    def change_path_favorite_button_color(self, fav_name, button_widget):
        if fav_name not in self.path_favorites: return

        current_fav_data = self.path_favorites[fav_name]
        current_color_hex = current_fav_data.get("color", self.DEFAULT_PATH_FAV_COLOR)

        dialog = CustomColorPickerDialog(self.predefined_colors, current_color_hex, self)
        if dialog.exec_() == QDialog.Accepted:
            new_color_hex = dialog.get_selected_color()
            if new_color_hex:
                self.path_favorites[fav_name]["color"] = new_color_hex
                button_widget.setStyleSheet(f"background-color: {new_color_hex}; padding: 2px 5px; border: 1px solid gray;")
                self.save_path_favorites_config()
                self.statusBar().showMessage(f"경로 즐겨찾기 '{fav_name}'의 색상이 변경되었습니다.", 2000)

    def save_path_favorites_config(self):
        config_path = self.get_app_config_path(self.PATH_FAVORITES_CONFIG_FILENAME)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.path_favorites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "저장 오류", f"경로 즐겨찾기 저장 중 오류 발생: {e}")

    def load_path_favorites_config(self):
        config_path = self.get_app_config_path(self.PATH_FAVORITES_CONFIG_FILENAME)
        temp_path_favorites = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        for name, data in loaded_data.items():
                            if isinstance(data, dict) and "path" in data:
                                temp_path_favorites[name] = data
                            elif isinstance(data, str): # 이전 버전 호환
                                temp_path_favorites[name] = {"path": data, "color": self.DEFAULT_PATH_FAV_COLOR}
            except Exception as e:
                print(f"경로 즐겨찾기 설정({config_path}) 불러오기 오류: {e}")
        self.path_favorites = temp_path_favorites

    def reset_path_favorites_dialog(self):
        reply = QMessageBox.question(self, "경로 즐겨찾기 초기화",
                                     "저장된 모든 경로 즐겨찾기를 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.path_favorites.clear()
            self.update_path_favorite_buttons_ui()
            try:
                path_fav_file = self.get_app_config_path(self.PATH_FAVORITES_CONFIG_FILENAME)
                if os.path.exists(path_fav_file):
                    os.remove(path_fav_file)
                self.statusBar().showMessage("모든 경로 즐겨찾기가 초기화되었습니다.", 3000)
            except Exception as e:
                QMessageBox.warning(self, "파일 삭제 오류", f"경로 즐겨찾기 파일 삭제 중 오류: {e}")

    def get_app_config_path(self, filename):
        config_dir = os.path.join(os.getenv('APPDATA') or os.path.expanduser("~"), "MyMultiExplorer")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, filename)

    def save_current_state_as_default(self):
            session_file_path = self.get_app_config_path(self.SESSION_CONFIG_FILENAME)
            panel_paths_in_order = [p.model.filePath(p.tree.rootIndex()) for p in self.panels_in_logical_order]

            top_splitter = self.content_area_host.findChild(QSplitter)
            saved_states = None
            if top_splitter:
                saved_states = self.save_splitter_states(top_splitter)

            layout_data = {
                "layout_mode": "ROW_MODE" if self.current_layout_mode == MainWindow.ROW_MODE else "COL_MODE",
                "line_capacities": self.line_capacities,
                "panel_paths": panel_paths_in_order,
                "splitter_states": saved_states
            }

            try:
                with open(session_file_path, 'w', encoding='utf-8') as f:
                    json.dump(layout_data, f, ensure_ascii=False, indent=2)

                self.save_path_favorites_config()
                self.save_favorites_config()

                self.statusBar().showMessage("현재 상태가 시작창으로 저장되었습니다.", 3000)
            except Exception as e:
                QMessageBox.critical(self, "시작창으로 저장 오류", f"저장 중 오류 발생: {e}")

    def load_default_session(self):
        session_file_path = self.get_app_config_path(self.SESSION_CONFIG_FILENAME)
        if not os.path.exists(session_file_path):
            QMessageBox.information(self, "시작창", "저장된 시작창 설정이 없습니다.")
            return
        if self.load_layout_from_file(session_file_path, is_session_load_for_panels_only=False):
            self.statusBar().showMessage("저장된 시작창 레이아웃을 불러왔습니다.", 3000)
        else: QMessageBox.warning(self, "오류", "시작창 레이아웃을 불러오는 데 실패했습니다.")

    def reset_layouts_dialog(self):
        reply = QMessageBox.question(self, "레이아웃 즐겨찾기 초기화",
                                     "저장된 모든 레이아웃 즐겨찾기를 삭제하시겠습니까?\n(현재 열린 탐색기와 경로 즐겨찾기는 유지됩니다)",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.perform_layout_reset()

    def perform_layout_reset(self):
        self.favorite_layouts.clear()
        self.update_favorite_buttons_ui()
        try:
            favorites_file = self.get_app_config_path(self.FAVORITES_CONFIG_FILENAME)
            if os.path.exists(favorites_file):
                os.remove(favorites_file)

            fav_layouts_dir = os.path.join(os.getenv('APPDATA') or os.path.expanduser("~"), "MyMultiExplorer", "FavoriteLayouts")
            if os.path.isdir(fav_layouts_dir):
                shutil.rmtree(fav_layouts_dir)

            self.statusBar().showMessage("모든 레이아웃 즐겨찾기가 초기화되었습니다.", 3000)
        except Exception as e:
            QMessageBox.warning(self, "초기화 오류", f"레이아웃 즐겨찾기 초기화 중 오류 발생: {e}")

    def show_favorite_button_context_menu(self, fav_name, button_widget, pos):
        context_menu = QMenu(self)
        context_menu.setAttribute(Qt.WA_DeleteOnClose)
        change_color_action = context_menu.addAction("버튼 색상 변경...")
        context_menu.addSeparator()
        delete_action = context_menu.addAction(f"'{fav_name}' 즐겨찾기 삭제")
        action = context_menu.exec_(button_widget.mapToGlobal(pos))
        if action == delete_action:
            QTimer.singleShot(0, lambda: self.delete_favorite_slot_and_refocus(fav_name))
        elif action == change_color_action:
            QTimer.singleShot(0, lambda: self.change_favorite_button_color_and_refocus(fav_name, button_widget))

    def delete_favorite_slot_and_refocus(self, fav_name):
        self.delete_favorite_slot(fav_name)
        QTimer.singleShot(10, lambda: self.activateWindow())
        QTimer.singleShot(20, lambda: self.setFocus())

    def change_favorite_button_color_and_refocus(self, fav_name, button_widget):
        self.change_favorite_button_color(fav_name, button_widget)
        QTimer.singleShot(10, lambda: self.activateWindow())
        QTimer.singleShot(20, lambda: self.setFocus())

    def change_favorite_button_color(self, fav_name, button_widget):
        if fav_name not in self.favorite_layouts: return
        current_fav_data = self.favorite_layouts[fav_name]
        current_color_hex = current_fav_data.get("color", "white") if isinstance(current_fav_data, dict) else "white"
        dialog = CustomColorPickerDialog(self.predefined_colors, current_color_hex, self)
        if dialog.exec_() == QDialog.Accepted:
            new_color_hex = dialog.get_selected_color()
            if new_color_hex:
                if isinstance(self.favorite_layouts[fav_name], dict):
                    self.favorite_layouts[fav_name]["color"] = new_color_hex
                else: self.favorite_layouts[fav_name] = {"path": str(self.favorite_layouts[fav_name]), "color": new_color_hex}
                base_style = f"background-color: {new_color_hex}; padding: 2px 5px; border: 1px solid gray;"
                filepath = self.favorite_layouts[fav_name].get("path", "")
                if not filepath or not os.path.exists(filepath):
                    button_widget.setStyleSheet(base_style + "color: gray; font-style: italic;")
                else: button_widget.setStyleSheet(base_style + "font-weight: bold;")
                self.save_favorites_config()
                self.statusBar().showMessage(f"'{fav_name}' 버튼 색상이 변경되었습니다.", 2000)

    def add_new_favorite_slot(self):
        if len(self.favorite_layouts) >= self.FAVORITE_COUNT:
            QMessageBox.information(self, "레이아웃 즐겨찾기", f"최대 {self.FAVORITE_COUNT}개만 추가 가능합니다.")
            return
        fav_name, ok = QInputDialog.getText(self, "새 레이아웃 즐겨찾기 이름", "새 즐겨찾기의 이름을 입력하세요:")
        if ok and fav_name:
            fav_name = fav_name.strip()
            if not fav_name:
                QMessageBox.warning(self, "이름 오류", "즐겨찾기 이름은 비워둘 수 없습니다.")
                return
            if fav_name in self.favorite_layouts:
                QMessageBox.warning(self, "이름 중복", "이미 사용 중인 이름입니다.")
                return
            self.save_current_layout_to_favorite_slot(fav_name, None)

    def save_current_layout_to_favorite_slot(self, fav_name, existing_filepath=None):
        filepath_to_save = existing_filepath
        favorites_storage_dir = os.path.join(os.getenv('APPDATA') or os.path.expanduser("~"), "MyMultiExplorer", "FavoriteLayouts")
        os.makedirs(favorites_storage_dir, exist_ok=True)
        if not filepath_to_save:
            safe_filename_base = "".join(c if c.isalnum() else "_" for c in fav_name)
            temp_filename = f"{safe_filename_base}.json"
            counter = 1
            filepath_to_save = os.path.join(favorites_storage_dir, temp_filename)
            while os.path.exists(filepath_to_save):
                temp_filename = f"{safe_filename_base}_{counter}.json"
                filepath_to_save = os.path.join(favorites_storage_dir, temp_filename)
                counter +=1

        if os.path.exists(filepath_to_save) and existing_filepath:
            reply = QMessageBox.question(self, "덮어쓰기 확인", f"'{fav_name}' 즐겨찾기를 덮어쓰시겠습니까?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.No: return

        if self.save_layout_to_file(filepath_to_save, include_favorites=False):
            current_fav_data = self.favorite_layouts.get(fav_name, {})
            current_color = current_fav_data.get("color", "#c1e9eb") if isinstance(current_fav_data, dict) else "#c1e9eb" # 즐겨찾기 기본색상
            self.favorite_layouts[fav_name] = {"path": filepath_to_save, "color": current_color}
            self.save_favorites_config()
            self.update_favorite_buttons_ui()
            self.statusBar().showMessage(f"레이아웃을 '{fav_name}' 즐겨찾기에 저장했습니다.", 3000)

    def load_layout_from_favorite_slot(self, fav_name):
        fav_data = self.favorite_layouts.get(fav_name)
        filepath_to_load = fav_data.get("path") if isinstance(fav_data, dict) else fav_data
        if filepath_to_load and os.path.exists(filepath_to_load):
            if self.load_layout_from_file(filepath_to_load, is_session_load_for_panels_only=False):
                self.statusBar().showMessage(f"'{fav_name}' 레이아웃을 불러왔습니다.", 3000)
                self.update_favorite_buttons_ui()
        else: QMessageBox.information(self, "즐겨찾기", f"'{fav_name}'에 연결된 레이아웃 파일을 찾을 수 없습니다.")

    def delete_favorite_slot(self, fav_name):
        if fav_name not in self.favorite_layouts: return
        reply = QMessageBox.question(self, "즐겨찾기 삭제", f"'{fav_name}' 즐겨찾기를 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try: del self.favorite_layouts[fav_name]
            except KeyError: pass
            self.save_favorites_config()
            self.update_favorite_buttons_ui()
            self.statusBar().showMessage(f"'{fav_name}' 즐겨찾기가 삭제되었습니다.", 2000)

    def get_favorites_config_filepath(self):
        return self.get_app_config_path(self.FAVORITES_CONFIG_FILENAME)

    def save_favorites_config(self):
        config_path = self.get_favorites_config_filepath()
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.favorite_layouts, f, ensure_ascii=False, indent=2)
        except Exception as e: print(f"즐겨찾기 설정 저장 오류 ({config_path}): {e}")

    def load_favorites_config(self):
        config_path = self.get_favorites_config_filepath()
        temp_favorite_layouts = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        for name, data in loaded_data.items():
                            if isinstance(data, dict) and "path" in data: temp_favorite_layouts[name] = data
                            elif isinstance(data, str): temp_favorite_layouts[name] = {"path": data, "color": "white"}
            except Exception as e: print(f"즐겨찾기 설정({config_path}) 불러오기 오류: {e}")
        self.favorite_layouts = temp_favorite_layouts

    def setup_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        company_label = QLabel("ⓒ 2025 Mk-TECH CO.LTD,  사용문의: 내선 1206")
        company_label.setStyleSheet("color: BLACK; font-size: 10pt;")
        status_bar.addPermanentWidget(company_label)

    def clear_dynamic_content(self):
        while self.content_area_host_layout.count() > 0:
            item = self.content_area_host_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

    def save_splitter_states(self, splitter_widget):
        if not isinstance(splitter_widget, QSplitter):
            return None

        states = [splitter_widget.sizes()]
        child_states = []
        for i in range(splitter_widget.count()):
            widget = splitter_widget.widget(i)
            child_states.append(self.save_splitter_states(widget))
        states.append(child_states)
        return states

    def restore_splitter_states(self, splitter_widget, states):
        if not all([isinstance(splitter_widget, QSplitter), states, len(states) == 2]):
            return

        try:
            if sum(states[0]) > 0:
                splitter_widget.setSizes(states[0])
        except Exception as e:
            print(f"스플리터 크기 복원 오류: {e}")

        child_states = states[1]
        for i in range(min(splitter_widget.count(), len(child_states))):
            widget = splitter_widget.widget(i)
            if child_states[i]:
                self.restore_splitter_states(widget, child_states[i])

    def distribute_splitter_sizes_equally(self, splitter_widget):
        if not isinstance(splitter_widget, QSplitter) or splitter_widget.count() == 0: return
        total_size = splitter_widget.width() if splitter_widget.orientation() == Qt.Horizontal else splitter_widget.height()
        if total_size > 10 and splitter_widget.count() > 0:
            count = splitter_widget.count()
            sizes = [total_size // count] * count
            for i in range(total_size % count): sizes[i] += 1
            try: splitter_widget.setSizes(sizes)
            except Exception as e: print(f"Error in setSizes: {e}")
        for i in range(splitter_widget.count()):
            child_widget = splitter_widget.widget(i)
            if isinstance(child_widget, QSplitter): self.distribute_splitter_sizes_equally(child_widget)

    def apply_splitter_sizes(self, splitter_widget):
        if self.last_splitter_states:
            self.restore_splitter_states(splitter_widget, self.last_splitter_states)
            self.last_splitter_states = None
        else:
            self.distribute_splitter_sizes_equally(splitter_widget)

    def rebuild_ui_from_structure(self):
        if self.last_splitter_states is None:
            current_top_splitter = self.content_area_host.findChild(QSplitter)
            if current_top_splitter:
                self.last_splitter_states = self.save_splitter_states(current_top_splitter)

        self.clear_dynamic_content()
        if not self.panels_in_logical_order: return
        main_splitter_orientation = Qt.Vertical if self.current_layout_mode == MainWindow.ROW_MODE else Qt.Horizontal
        main_splitter = QSplitter(main_splitter_orientation)
        main_splitter.setChildrenCollapsible(False)
        self.content_area_host_layout.addWidget(main_splitter, 1)
        if self.current_layout_mode == MainWindow.ROW_MODE:
            self.panel_grid_structure = self._calculate_panel_grid_structure()
            for panel_row_list in self.panel_grid_structure:
                if not panel_row_list: continue
                row_splitter = QSplitter(Qt.Horizontal)
                row_splitter.setChildrenCollapsible(False)
                for panel in panel_row_list: row_splitter.addWidget(panel)
                if row_splitter.count() > 0 : main_splitter.addWidget(row_splitter)
                else: row_splitter.deleteLater()
        elif self.current_layout_mode == MainWindow.COL_MODE:
            panel_iter = iter(self.panels_in_logical_order)
            panels_left_to_place = True
            current_col_caps = self.line_capacities if any(c > 0 for c in self.line_capacities) else list(self.DEFAULT_LINE_CAPACITIES)
            cap_idx = 0
            while panels_left_to_place:
                capacity = current_col_caps[cap_idx] if cap_idx < len(current_col_caps) else current_col_caps[-1]
                if capacity <= 0: capacity = 1
                col_splitter = QSplitter(Qt.Vertical)
                col_splitter.setChildrenCollapsible(False)
                panels_in_current_col = 0
                try:
                    for _ in range(capacity):
                        col_splitter.addWidget(next(panel_iter))
                        panels_in_current_col += 1
                except StopIteration: panels_left_to_place = False
                if panels_in_current_col > 0: main_splitter.addWidget(col_splitter)
                else: col_splitter.deleteLater()
                if not panels_left_to_place: break
                cap_idx +=1
        if main_splitter.count() == 0 and self.panels_in_logical_order:
            for panel in self.panels_in_logical_order: main_splitter.addWidget(panel)

        QTimer.singleShot(0, lambda ms=main_splitter: self.apply_splitter_sizes(ms))

    def toggle_overall_layout_mode(self):
        self.current_layout_mode = MainWindow.COL_MODE if self.current_layout_mode == MainWindow.ROW_MODE else MainWindow.ROW_MODE
        self.rebuild_ui_from_structure()
        self.statusBar().showMessage(f"{'열' if self.current_layout_mode == MainWindow.COL_MODE else '단'} 모드로 변경됨", 2000)

    def _calculate_panel_grid_structure(self):
        new_grid_structure = []
        panel_iter = iter(self.panels_in_logical_order)
        current_line_caps = self.line_capacities if any(c > 0 for c in self.line_capacities) else list(self.DEFAULT_LINE_CAPACITIES)
        cap_idx = 0
        panels_remaining = True
        while panels_remaining:
            capacity = current_line_caps[cap_idx] if cap_idx < len(current_line_caps) else current_line_caps[-1]
            if capacity <= 0: capacity = 1
            current_line_list = []
            try:
                for _ in range(capacity): current_line_list.append(next(panel_iter))
            except StopIteration: panels_remaining = False
            if current_line_list: new_grid_structure.append(current_line_list)
            if not panels_remaining: break
            cap_idx += 1
        return new_grid_structure if new_grid_structure else [[]]

    def add_explorer_panel(self, path=''):
        panel = ExplorerPanel(path)
        panel.delete_button.clicked.connect(functools.partial(self.request_panel_removal, panel))
        panel.request_new_panel.connect(self.add_explorer_panel)
        self.panels_in_logical_order.append(panel)
        self.rebuild_ui_from_structure()

    def request_panel_removal(self, panel_to_remove, rebuild_after=True):
        if panel_to_remove in self.panels_in_logical_order:
            self.panels_in_logical_order.remove(panel_to_remove)
            panel_to_remove.deleteLater()
            if rebuild_after: self.rebuild_ui_from_structure()

    def set_line_capacities_config(self):
        current_caps_str = ",".join(map(str, self.line_capacities))
        text, ok = QInputDialog.getText(self, "최대 설정", "패널 수를 콤마(,)로 구분하여 입력:", text=current_caps_str)
        if ok:
            if text.strip():
                try:
                    new_caps = [int(x.strip()) for x in text.split(',') if x.strip().isdigit() and int(x.strip()) > 0]
                    if not new_caps:
                         QMessageBox.warning(self, "입력 오류", "유효한 숫자가 없습니다.")
                         new_caps = list(self.DEFAULT_LINE_CAPACITIES)
                    self.line_capacities = new_caps
                except ValueError: self.line_capacities = list(self.DEFAULT_LINE_CAPACITIES)
            else: self.line_capacities = list(self.DEFAULT_LINE_CAPACITIES)
            self.line_capacity_button.setText(f"최대: {','.join(map(str, self.line_capacities))}")
            self.rebuild_ui_from_structure()

    def save_layout_to_file(self, filepath, include_favorites=True):
        top_splitter = self.content_area_host.findChild(QSplitter)
        saved_states = None
        if top_splitter:
            saved_states = self.save_splitter_states(top_splitter)

        panel_paths = [p.model.filePath(p.tree.rootIndex()) for p in self.panels_in_logical_order]
        layout_data = {
            "layout_mode": "ROW_MODE" if self.current_layout_mode == MainWindow.ROW_MODE else "COL_MODE",
            "line_capacities": self.line_capacities,
            "panel_paths": panel_paths,
            "splitter_states": saved_states
        }
        if include_favorites: layout_data["favorite_layouts"] = self.favorite_layouts
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"레이아웃 저장 중 오류 발생: {e}")
            return False

    def load_layout_from_file(self, filepath, is_session_load_for_panels_only=False):
        if not filepath or not os.path.exists(filepath):
            if not is_session_load_for_panels_only:
                QMessageBox.warning(self, "불러오기 오류", f"파일을 찾을 수 없습니다: {filepath}")
            return False
        try:
            with open(filepath, 'r', encoding='utf-8') as f: layout_data = json.load(f)

            self.last_splitter_states = layout_data.get("splitter_states", None)

            for panel in list(self.panels_in_logical_order):
                self.request_panel_removal(panel, rebuild_after=False)
            self.panels_in_logical_order.clear()

            mode_str = layout_data.get("layout_mode", "ROW_MODE")
            self.current_layout_mode = MainWindow.ROW_MODE if mode_str == "ROW_MODE" else MainWindow.COL_MODE

            loaded_caps = layout_data.get("line_capacities", list(self.DEFAULT_LINE_CAPACITIES))
            if isinstance(loaded_caps, list) and all(isinstance(x, int) and x > 0 for x in loaded_caps) and loaded_caps:
                self.line_capacities = loaded_caps
            else:
                self.line_capacities = list(self.DEFAULT_LINE_CAPACITIES)
            self.line_capacity_button.setText(f"최대: {','.join(map(str, self.line_capacities))}")

            panel_paths = layout_data.get("panel_paths", [])

            if panel_paths:
                for path in panel_paths:
                    panel = ExplorerPanel(path)
                    panel.delete_button.clicked.connect(functools.partial(self.request_panel_removal, panel))
                    panel.request_new_panel.connect(self.add_explorer_panel)
                    self.panels_in_logical_order.append(panel)

            self.rebuild_ui_from_structure()
            return True
        except Exception as e:
            import traceback
            print(f"레이아웃 파일 로드 실패: {e}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "불러오기 오류", f"레이아웃 파일 처리 중 오류 발생:\n{e}")
            return False
# --- 애플리케이션 실행 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())