import os
import re
import shutil
import sys
from collections import Counter
from enum import Enum
from typing import Any

import pandas as pd
import platformdirs
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

__version__ = "1.0.6"


def get_settings() -> QSettings:
    """
    Return a shared QSettings instance in user space (.ini file).
    """
    settings = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        QCoreApplication.organizationName(),
        QCoreApplication.applicationName(),
    )
    return settings


def get_formatted_photo_name(photos_format: str, photo_number: int) -> str:
    """
    Return the formatted photo name based on the given format and photo number.
    """
    match = re.search(r"(#+)", photos_format)
    if not match:
        raise ValueError("Invalid photos format: no '#' found.")

    num_hashes = len(match.group(0))
    return photos_format.replace(match.group(0), str(photo_number).zfill(num_hashes))


class CopyOutcome(Enum):
    SUCCESS = 1
    FINISH_ERRORS = 2
    FAILURE = 3


class DeleteOutcome(Enum):
    SUCCESS = 1
    FAILURE = 2
    CANCELED = 3


class CopyThread(QThread):
    progress = pyqtSignal(int)
    update_log = pyqtSignal(str)
    finished = pyqtSignal(CopyOutcome)

    def __init__(
        self,
        source_dir: str,
        dest_dir: str,
        photos: Counter[str],
        photos_ext: str = "",
        photos_format: str = "",
    ) -> None:
        super().__init__()
        self.source_dir: str = source_dir
        self.dest_dir: str = dest_dir
        self.photos: Counter[str] = photos
        self.photos_ext: str = photos_ext
        self.photos_format: str = photos_format
        self.__total_photos: int = photos.total()
        self.__copied_photos: int = 0

    def run(self) -> None:
        errors: bool = False
        if not self.photos_format:
            # Copy photos using the names in the file
            for photo, count in self.photos.items():
                if not self.copy_n_photos(photo, count):
                    errors = True
        else:
            for photo, count in self.photos.items():
                formatted_name = get_formatted_photo_name(
                    self.photos_format, int(photo)
                )
                if not self.copy_n_photos(formatted_name, count):
                    errors = True

        if errors:
            self.finished.emit(CopyOutcome.FINISH_ERRORS)
        else:
            self.finished.emit(CopyOutcome.SUCCESS)

    def copy_n_photos(self, photo: str, n: int) -> bool:
        """
        Copy a photo n times.
        Returns True if all copies were successful, False otherwise.
        """
        init_msg: str = f"A copiar foto {photo + self.photos_ext!r}" + (
            f" {n} vezes..." if n > 1 else "..."
        )

        self.update_log.emit(init_msg)
        all_copied = True

        src_file = os.path.join(self.source_dir, photo + self.photos_ext)
        for k in range(1, n + 1):
            out_photo: str = photo
            if n > 1:
                out_photo += f" ({k})"

            dest_file = os.path.join(self.dest_dir, out_photo + self.photos_ext)
            try:
                shutil.copyfile(src_file, dest_file)
                self.__copied_photos += 1
            except FileNotFoundError:
                k_missing: int = n - k + 1
                self.update_log.emit(
                    f"<span style='color: red;'>Ficheiro {photo + self.photos_ext!r} não encontrado (não foram copiadas {k_missing} fotos)!</span>"
                )
                all_copied = False
                self.__copied_photos += k_missing
                break
            except OSError as e:
                k_missing = n - k + 1
                self.update_log.emit(
                    f"<span style='color: red;'>Erro ao copiar foto {photo + self.photos_ext!r} (não foram copiadas {k_missing} fotos): {e}</span>"
                )
                all_copied = False
                self.__copied_photos += k_missing
                break
            finally:
                # Emit progress signal
                self.progress.emit(
                    int(self.__copied_photos / self.__total_photos * 100)
                )

        return all_copied


class DeleteThread(QThread):
    finished = pyqtSignal(DeleteOutcome)
    update_log = pyqtSignal(str)

    def __init__(self, folder_path: str) -> None:
        super().__init__()
        self.folder_path: str = folder_path
        self.__canceled: bool = False

    def run(self) -> None:
        outcome: DeleteOutcome = DeleteOutcome.SUCCESS
        for root, dirs, files in os.walk(self.folder_path, topdown=False):
            for f in files:
                if self.__canceled:
                    self.finished.emit(DeleteOutcome.CANCELED)
                    return
                path = os.path.join(root, f)
                self.update_log.emit(f"A apagar {path!r}...")
                try:
                    os.remove(path)
                except Exception as e:
                    self.update_log.emit(
                        f"<span style='color: red;'>Erro ao apagar {path!r}: {e}</span>"
                    )
                    outcome = DeleteOutcome.FAILURE
            for d in dirs:
                if self.__canceled:
                    self.finished.emit(DeleteOutcome.CANCELED)
                    return
                path = os.path.join(root, d)
                self.update_log.emit(f"A apagar {path!r}...")
                try:
                    os.rmdir(path)
                except Exception as e:
                    self.update_log.emit(
                        f"<span style='color: red;'>Erro ao apagar {path!r}: {e}</span>"
                    )
                    outcome = DeleteOutcome.FAILURE

        os.makedirs(self.folder_path, exist_ok=True)
        self.finished.emit(outcome)

    def cancel(self) -> None:
        """
        Cancel the deletion process
        """
        self.__canceled = True


class MyLabel(QLabel):
    def __init__(self, text: str, pointSize: int = 12) -> None:
        super().__init__(text)
        self.setWordWrap(True)
        # Increase font size
        font = self.font()
        font.setPointSize(pointSize)
        self.setFont(font)


class MyLineEdit(QLineEdit):
    def __init__(self, text: str, readOnly: bool = True) -> None:
        super().__init__()
        self.setReadOnly(readOnly)
        self.setText(text)
        # Increase font size
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)


class MyPushButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        # Increase font size
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)


class MyComboBox(QComboBox):
    def __init__(self) -> None:
        super().__init__()
        # Increase font size
        font = self.font()
        font.setPointSize(12)
        self.setFont(font)


class DeleteFolderDialog(QDialog):
    def __init__(self, folder_path: str) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(400, 200)

        self.folder_path: str = folder_path
        self.user_choice: bool = False

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(0)
        self.label = QLabel(
            f"A pasta de destino {os.path.basename(folder_path)!r} não está vazia.\n"
            "Apgagar o conteúdo existente e continuar?"
        )
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Increase font size
        font = self.label.font()
        font.setPointSize(12)
        self.label.setFont(font)
        layout.addWidget(self.label)
        layout.addStretch(0)

        self.yes_button = MyPushButton("Sim")
        self.yes_button.clicked.connect(self.yes)
        self.no_button = MyPushButton("Não")
        self.no_button.clicked.connect(self.no)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.no_button)
        buttons_layout.addWidget(self.yes_button)
        layout.addLayout(buttons_layout)
        layout.addStretch(0)

        self.setLayout(layout)

        self.yes_button.setFocus()

    def yes(self) -> None:
        """
        User chose to delete the folder contents
        """
        self.user_choice = True
        # Delete folder contents
        # Show progress dialog
        progress_dialog = self.ProgressDialog(self.folder_path, self)
        progress_dialog.accepted.connect(self.close)  # Close this dialog when done
        progress_dialog.rejected.connect(self.no)  # Treat cancel/failure as "No"
        progress_dialog.start()

    def no(self) -> None:
        """
        User chose not to delete the folder contents
        """
        self.user_choice = False
        self.close()

    class ProgressDialog(QDialog):
        def __init__(self, folder_path: str, parent: QWidget) -> None:
            super().__init__(parent)
            self.setWindowTitle(QCoreApplication.applicationName())
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.setFixedSize(300, 100)

            layout = QVBoxLayout()
            layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            layout.addStretch(1)

            self.label = MyLabel(
                f"A apagar o conteúdo de {os.path.basename(folder_path)!r}..."
            )
            layout.addWidget(self.label)
            layout.addStretch(1)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            layout.addWidget(self.progress_bar)
            layout.addStretch(1)

            self.cancel_button = MyPushButton("Cancelar")
            self.cancel_button.clicked.connect(self.cancel)
            layout.addWidget(self.cancel_button)
            layout.addStretch(1)

            self.setLayout(layout)

            self.deleteThread = DeleteThread(folder_path)
            self.deleteThread.finished.connect(self.handle_finished)
            self.deleteThread.update_log.connect(self.label.setText)

        def cancel(self) -> None:
            """
            User chose to cancel the deletion
            """
            if self.deleteThread.isRunning():
                self.deleteThread.cancel()

        def start(self) -> None:
            """
            Show the dialog and start the deletion thread
            """
            super().show()
            self.deleteThread.start()

        def handle_finished(self, success: DeleteOutcome) -> None:
            """
            Handle the completion of the deletion process
            """
            if success == DeleteOutcome.FAILURE:
                error_dialog = QDialog(self)
                error_dialog.setWindowTitle("Erro")
                error_dialog.setFixedSize(300, 100)
                error_layout = QVBoxLayout()
                error_label = QLabel("Ocorreu um erro ao apagar alguns ficheiros.")
                error_label.setWordWrap(True)
                error_layout.addWidget(error_label)
                ok_button = MyPushButton("OK")
                ok_button.clicked.connect(error_dialog.close)
                button_layout = QHBoxLayout()
                button_layout.addStretch(1)
                button_layout.addWidget(ok_button)
                button_layout.addStretch(1)
                error_layout.addLayout(button_layout)
                error_dialog.setLayout(error_layout)
                error_dialog.exec()
                self.reject()
            elif success == DeleteOutcome.CANCELED:
                self.reject()
            else:
                self.accept()


class InitWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        self.label = QLabel(QCoreApplication.applicationName())
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Increase font size
        font = self.label.font()
        font.setPointSize(20)
        self.label.setFont(font)
        layout.addWidget(self.label)

        self.version_label = QLabel(f"Versão: {QCoreApplication.applicationVersion()}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font.setPointSize(8)
        font.setItalic(True)
        self.version_label.setFont(font)
        layout.addWidget(self.version_label)
        layout.addStretch()

        self.info_label = MyLabel("Copiar fotos a partir de:")
        layout.addWidget(self.info_label)

        self.file_window = FileSelectionWindow(self)
        self.file_button = MyPushButton("Ficheiro")
        self.file_button.clicked.connect(self.open_file_window)
        layout.addWidget(self.file_button)

        self.folder_window = FolderSelectionWindow(self)
        self.folder_button = MyPushButton("Pasta")
        self.folder_button.clicked.connect(self.open_folder_window)
        layout.addWidget(self.folder_button)
        layout.addStretch()

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def open_file_window(self) -> None:
        """
        Goes to the file selection window
        """
        self.file_window.show()
        self.close()

    def open_folder_window(self) -> None:
        """
        Goes to the folder selection window
        """
        self.folder_window.show()
        self.close()


class FileSelectionWindow(QMainWindow):
    def __init__(self, main_window: InitWindow) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(600, 450)

        self.main_window = main_window
        self.next_window = CopyWindow()

        self.settings = get_settings()
        self.file_path: str = self.settings.value("file_path", "", type=str)
        self.source_dir: str = self.settings.value("source_dir", "", type=str)
        self.photos_format: str = self.settings.value("photos_format", "###", type=str)
        self.dest_dir: str = self.settings.value("dest_dir", "", type=str)

        layout = QVBoxLayout()

        # FILE
        self.file_label = MyLabel("Ficheiro com a lista de fotos a copiar:")
        self.file_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.file_label)

        self.file_line_edit = MyLineEdit("Selecionar ficheiro...")
        self.file_line_edit.textChanged.connect(self.content_changed)
        self.file_button = MyPushButton("Selecionar")
        self.file_button.clicked.connect(self.get_file_path)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_line_edit)
        file_layout.addWidget(self.file_button)
        file_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(file_layout)

        # PHOTOS DIR
        self.source_dir_label = MyLabel("Pasta com as fotos:")
        self.source_dir_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.source_dir_label)

        self.source_dir_line_edit = MyLineEdit("Selecionar pasta...")
        self.source_dir_line_edit.textChanged.connect(self.content_changed)
        self.source_dir_button = MyPushButton("Selecionar")
        self.source_dir_button.clicked.connect(self.get_source_dir)
        source_dir_layout = QHBoxLayout()
        source_dir_layout.addWidget(self.source_dir_line_edit)
        source_dir_layout.addWidget(self.source_dir_button)
        source_dir_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(source_dir_layout)

        # PHOTOS EXT
        self.photos_ext_label = MyLabel("Extensão das fotos:")
        self.photos_ext_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.photos_ext_combo = MyComboBox()
        self.photos_ext_combo.addItems([".jpg", ".cr3", "Outra..."])
        self.photos_ext_combo.currentIndexChanged.connect(self.on_ext_combo_change)
        self.photos_ext_combo.currentIndexChanged.connect(self.content_changed)
        self.photos_ext_edit = MyLineEdit("", readOnly=False)
        self.photos_ext_edit.setMinimumWidth(75)
        self.photos_ext_edit.hide()
        self.photos_ext_edit.textChanged.connect(self.on_ext_edit_change)
        self.photos_ext_edit.textChanged.connect(self.content_changed)
        photos_ext_layout = QHBoxLayout()
        photos_ext_layout.addWidget(self.photos_ext_label)
        photos_ext_layout.addWidget(self.photos_ext_combo)
        photos_ext_layout.addWidget(self.photos_ext_edit)
        photos_ext_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        photos_ext_layout.setContentsMargins(0, 0, 10, 10)
        layout.addLayout(photos_ext_layout)

        # PHOTOS NAME FORMAT
        self.photos_format_label = MyLabel("Formato dos nomes das fotos:")
        self.photos_format_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.photos_format_label)
        self.photos_format_line_edit = MyLineEdit("", readOnly=False)
        self.photos_format_line_edit.setFixedWidth(250)
        self.photos_format_example = MyLabel("", 10)
        self.photos_format_line_edit.textChanged.connect(self.on_photos_format_change)
        self.photos_format_layout = QHBoxLayout()
        self.photos_format_layout.addWidget(self.photos_format_line_edit)
        self.photos_format_layout.addWidget(self.photos_format_example)
        self.photos_format_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.photos_format_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(self.photos_format_layout)

        # OUTPUT DIR
        self.dest_dir_label = MyLabel("Pasta de destino:")
        self.dest_dir_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.dest_dir_label)

        self.dest_dir_line_edit = MyLineEdit("Selecionar pasta...")
        self.dest_dir_line_edit.textChanged.connect(self.content_changed)
        self.dest_dir_button = MyPushButton("Selecionar")
        self.dest_dir_button.clicked.connect(self.get_dest_dir)
        dest_dir_layout = QHBoxLayout()
        dest_dir_layout.addWidget(self.dest_dir_line_edit)
        dest_dir_layout.addWidget(self.dest_dir_button)
        dest_dir_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(dest_dir_layout)

        # WINDOWS BUTTONS
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons_layout.setContentsMargins(0, 0, 0, 10)

        self.back_button = MyPushButton("Voltar")
        self.back_button.clicked.connect(self.back)
        buttons_layout.addWidget(self.back_button)

        self.next_button = MyPushButton("Próximo")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next)
        buttons_layout.addWidget(self.next_button)

        layout.addLayout(buttons_layout)

        # Set previous values and booleans
        self.file_bool: bool = False
        self.source_bool: bool = False
        self.photos_ext_bool: bool = True
        self.photos_format_bool: bool = False
        self.dest_bool: bool = False

        if self.file_path:
            self.file_bool = True
            self.file_line_edit.setText(self.file_path)

        if self.source_dir:
            self.source_bool = True
            self.source_dir_line_edit.setText(self.source_dir)

        self.photos_format_line_edit.setText(self.photos_format)

        if self.dest_dir and self.dest_dir != self.source_dir:
            self.dest_bool = True
            self.dest_dir_line_edit.setText(self.dest_dir)
        elif self.dest_dir == self.source_dir:
            self.dest_dir = ""

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def get_file_path(self) -> None:
        """
        Returns the path of the file selected by the user
        """
        if not self.file_path and not hasattr(self, "initial_path"):
            self.initial_path: str = platformdirs.user_desktop_dir()
        else:
            self.initial_path = os.path.dirname(self.file_path)

        file_path, _ = QFileDialog.getOpenFileName(
            caption="Selecionar ficheiro com lista de fotos a copiar",
            directory=self.initial_path,
            filter="Documento de texto (*.txt);;Ficheiro Excel (*.xls *.xlsx)",
            initialFilter="Ficheiro Excel (*.xls *.xlsx)",
        )

        if file_path:
            self.file_bool = True
            self.file_path = file_path
            self.file_line_edit.setText(file_path)
            self.initial_path = os.path.dirname(file_path)
        elif not self.file_path:
            self.file_bool = False
            self.file_line_edit.setText("Ficheiro não selecionado")

    def get_source_dir(self) -> None:
        """
        Returns the path of the photos directory selected by the user
        """
        if not self.source_dir and not hasattr(self, "initial_path"):
            self.initial_path = platformdirs.user_desktop_dir()
        else:
            self.initial_path = self.source_dir

        source_dir = QFileDialog.getExistingDirectory(
            caption="Selecionar pasta com as fotos",
            directory=self.initial_path,
            options=QFileDialog.Option.HideNameFilterDetails,
        )

        if source_dir:
            if source_dir == self.dest_dir:
                self.source_bool = False
                self.source_dir = ""
                self.source_dir_line_edit.setText(
                    "Atenção: pasta das fotos igual à pasta de destino"
                )
                self.source_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.source_bool = True
                self.source_dir = source_dir
                self.source_dir_line_edit.setText(source_dir)
                self.source_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = source_dir
        elif not self.source_dir:
            self.source_bool = False
            self.source_dir_line_edit.setText("Pasta não selecionada")

    def get_dest_dir(self) -> None:
        """
        Returns the path of the output directory selected by the user
        """
        if not self.dest_dir and not hasattr(self, "initial_path"):
            self.initial_path = platformdirs.user_desktop_dir()
        else:
            self.initial_path = self.dest_dir

        dest_dir = QFileDialog.getExistingDirectory(
            caption="Selecionar pasta de destino para as fotos",
            directory=self.initial_path,
            options=QFileDialog.Option.HideNameFilterDetails,
        )

        if dest_dir:
            if dest_dir == self.source_dir:
                self.dest_bool = False
                self.dest_dir = ""
                self.dest_dir_line_edit.setText(
                    "Atenção: pasta de destino igual à pasta das fotos"
                )
                self.dest_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.dest_bool = True
                self.dest_dir = dest_dir
                self.dest_dir_line_edit.setText(dest_dir)
                self.dest_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = dest_dir
        elif not self.dest_dir:
            self.dest_bool = False
            self.dest_dir_line_edit.setText("Pasta não selecionada")

    def on_ext_combo_change(self) -> None:
        """
        Shows or hides the line edit for custom photo extension
        """
        if self.photos_ext_combo.currentText() == "Outra...":
            self.photos_ext_bool = False
            self.photos_ext_edit.setText(".")
            self.photos_ext_edit.show()
            self.photos_ext_edit.setFocus()
        else:
            self.photos_ext_bool = True
            self.photos_ext_edit.hide()

    def on_ext_edit_change(self, text: str) -> None:
        """
        Validates the custom photo extension
        """
        pattern = re.compile(r"^(\.[a-zA-Z0-9]+)+$")
        text = text.strip().lower()

        self.photos_ext_edit.blockSignals(True)
        self.photos_ext_edit.setText(text)

        if not text.startswith("."):
            text = "." + text
            self.photos_ext_edit.setText(text)

        self.photos_ext_edit.blockSignals(False)

        self.photos_ext_bool = pattern.match(text) is not None

    def on_photos_format_change(self, text: str) -> None:
        """
        Validates the photos name format
        """
        invalid_chars = r'[<>:"/\\|?*\']'
        if re.search(invalid_chars, text):
            self.photos_format_example.setText("(Caracteres inválidos: <>:\"/\\|?*')")
            self.photos_format_example.setStyleSheet("color: red;")
            self.photos_format_bool = False
            return

        text = text.strip()
        if not text:
            self.photos_format_example.setText("(A usar o nome indicado no ficheiro)")
            self.photos_format_example.setStyleSheet("color: black;")
            self.photos_format = ""
            self.photos_format_bool = True
            return

        matches = re.findall(r"(#+)", text)
        if not matches:
            self.photos_format_example.setText("(Use # para indicar números)")
            self.photos_format_example.setStyleSheet("color: red;")
            self.photos_format_bool = False
            return
        elif len(matches) > 1:
            self.photos_format_example.setText("(Apenas um grupo de # é permitido)")
            self.photos_format_example.setStyleSheet("color: red;")
            self.photos_format_bool = False
            return
        else:
            self.photos_format_example.setStyleSheet("color: black;")

        self.photos_format = text
        self.photos_format_bool = True

        example: str = (
            "Ex.: "
            + get_formatted_photo_name(text, 0)
            + ", "
            + get_formatted_photo_name(text, 1)
            + ", ..."
        )
        self.photos_format_example.setText(example)

    def content_changed(self) -> None:
        """
        Checks if the content of the widgets is valid to enable the next button
        """
        if (
            self.file_bool
            and self.source_bool
            and self.photos_ext_bool
            and self.photos_format_bool
            and self.dest_bool
        ):
            self.next_button.setEnabled(True)
        else:
            self.next_button.setEnabled(False)

    def back(self) -> None:
        """
        Goes to the previous window
        """
        self.main_window.show()
        self.close()

    def next(self) -> None:
        """
        Goes to the next window
        """
        if not self.file_path or not self.source_dir or not self.dest_dir:
            return
        else:
            self.settings.setValue("file_path", self.file_path)
            self.settings.setValue("source_dir", self.source_dir)
            self.settings.setValue("dest_dir", self.dest_dir)
            self.settings.setValue("photos_format", self.photos_format)

        self.photos_ext: str = self.photos_ext_combo.currentText()
        if self.photos_ext == "Outra...":
            self.photos_ext = self.photos_ext_edit.text().strip()

        # Check if dest_dir is empty
        if os.listdir(self.dest_dir):
            dialog = DeleteFolderDialog(self.dest_dir)
            dialog.exec()
            if not dialog.user_choice:
                # User chose not to delete contents or canceled or there was an error
                return

        self.next_window.show()
        self.close()
        self.next_window.start_file_copy_process(
            self.file_path,
            self.source_dir,
            self.photos_ext,
            self.photos_format,
            self.dest_dir,
        )


class FolderSelectionWindow(QMainWindow):
    def __init__(self, main_window: QMainWindow) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(600, 250)

        self.main_window = main_window
        self.next_window = CopyWindow()

        self.settings = get_settings()
        self.folder_dir: str = self.settings.value("folder_dir", "", type=str)
        self.source_dir: str = self.settings.value("source_dir", "", type=str)
        self.dest_dir: str = self.settings.value("dest_dir", "", type=str)

        layout = QVBoxLayout()

        # FOLDER
        self.folder_label = MyLabel("Pasta com a lista de fotos a copiar:")
        self.folder_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.folder_label)

        self.folder_line_edit = MyLineEdit("Selecionar pasta...")
        self.folder_line_edit.textChanged.connect(self.content_changed)
        self.folder_button = MyPushButton("Selecionar")
        self.folder_button.clicked.connect(self.get_folder_path)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_line_edit)
        folder_layout.addWidget(self.folder_button)
        folder_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(folder_layout)

        # PHOTOS DIR
        self.source_dir_label = MyLabel("Pasta com as fotos:")
        self.source_dir_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.source_dir_label)

        self.source_dir_line_edit = MyLineEdit("Selecionar pasta...")
        self.source_dir_line_edit.textChanged.connect(self.content_changed)
        self.source_dir_button = MyPushButton("Selecionar")
        self.source_dir_button.clicked.connect(self.get_source_dir)
        source_dir_layout = QHBoxLayout()
        source_dir_layout.addWidget(self.source_dir_line_edit)
        source_dir_layout.addWidget(self.source_dir_button)
        source_dir_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(source_dir_layout)

        # OUTPUT DIR
        self.dest_dir_label = MyLabel("Pasta de destino:")
        self.dest_dir_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        layout.addWidget(self.dest_dir_label)

        self.dest_dir_line_edit = MyLineEdit("Selecionar pasta...")
        self.dest_dir_line_edit.textChanged.connect(self.content_changed)
        self.dest_dir_button = MyPushButton("Selecionar")
        self.dest_dir_button.clicked.connect(self.get_dest_dir)
        dest_dir_layout = QHBoxLayout()
        dest_dir_layout.addWidget(self.dest_dir_line_edit)
        dest_dir_layout.addWidget(self.dest_dir_button)
        dest_dir_layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(dest_dir_layout)

        # WINDOWS BUTTONS
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        buttons_layout.setContentsMargins(0, 0, 0, 10)

        self.back_button = MyPushButton("Voltar")
        self.back_button.clicked.connect(self.back)
        buttons_layout.addWidget(self.back_button)

        self.next_button = MyPushButton("Próximo")
        self.next_button.clicked.connect(self.next)
        self.next_button.setEnabled(False)
        buttons_layout.addWidget(self.next_button)

        layout.addLayout(buttons_layout)

        # Set previous values and booleans
        self.folder_bool: bool = False
        self.source_bool: bool = False
        self.dest_bool: bool = False

        if self.folder_dir:
            self.folder_bool = True
            self.folder_line_edit.setText(self.folder_dir)

        if self.source_dir and self.source_dir != self.folder_dir:
            self.source_bool = True
            self.source_dir_line_edit.setText(self.source_dir)
        elif self.source_dir == self.folder_dir:
            self.source_dir = ""

        if (
            self.dest_dir
            and self.dest_dir != self.folder_dir
            and self.dest_dir != self.source_dir
        ):
            self.dest_bool = True
            self.dest_dir_line_edit.setText(self.dest_dir)
        elif self.dest_dir == self.folder_dir or self.dest_dir == self.source_dir:
            self.dest_dir = ""

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def get_folder_path(self) -> None:
        """
        Returns the path of the folder selected by the user
        """
        if not self.folder_dir and not hasattr(self, "initial_path"):
            self.initial_path: str = platformdirs.user_desktop_dir()
        else:
            self.initial_path = self.folder_dir

        folder_dir = QFileDialog.getExistingDirectory(
            caption="Selecionar pasta com a lista de fotos a copiar",
            directory=self.initial_path,
            options=QFileDialog.Option.HideNameFilterDetails,
        )

        if folder_dir:
            if folder_dir == self.source_dir:
                self.folder_bool = False
                self.folder_dir = ""
                self.folder_line_edit.setText(
                    "Atenção: pasta da lista das fotos igual à pasta das fotos"
                )
                self.folder_line_edit.setStyleSheet("color: red;")
            elif folder_dir == self.dest_dir:
                self.folder_bool = False
                self.folder_dir = ""
                self.folder_line_edit.setText(
                    "Atenção: pasta da lista das fotos igual à pasta de destino"
                )
                self.folder_line_edit.setStyleSheet("color: red;")
            else:
                self.folder_bool = True
                self.folder_dir = folder_dir
                self.folder_line_edit.setText(folder_dir)
                self.folder_line_edit.setStyleSheet("color: black;")
                self.initial_path = folder_dir
        elif not self.folder_dir:
            self.folder_bool = False
            self.folder_line_edit.setText("Pasta não selecionada")

    def get_source_dir(self) -> None:
        """
        Returns the path of the photos directory selected by the user
        """
        if not self.source_dir and not hasattr(self, "initial_path"):
            self.initial_path = platformdirs.user_desktop_dir()
        else:
            self.initial_path = self.source_dir

            source_dir = QFileDialog.getExistingDirectory(
                caption="Selecionar pasta com as fotos",
                directory=self.initial_path,
                options=QFileDialog.Option.HideNameFilterDetails,
            )

        if source_dir:
            if source_dir == self.folder_dir:
                self.source_bool = False
                self.source_dir = ""
                self.source_dir_line_edit.setText(
                    "Atenção: pasta das fotos igual à pasta da lista das fotos"
                )
                self.source_dir_line_edit.setStyleSheet("color: red;")
            elif source_dir == self.dest_dir:
                self.source_bool = False
                self.source_dir = ""
                self.source_dir_line_edit.setText(
                    "Atenção: pasta das fotos igual à pasta de destino"
                )
                self.source_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.source_bool = True
                self.source_dir = source_dir
                self.source_dir_line_edit.setText(source_dir)
                self.source_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = source_dir
        elif not self.source_dir:
            self.source_bool = False
            self.source_dir_line_edit.setText("Pasta não selecionada")

    def get_dest_dir(self) -> None:
        """
        Returns the path of the output directory selected by the user
        """
        if not self.dest_dir and not hasattr(self, "initial_path"):
            self.initial_path = platformdirs.user_desktop_dir()
        else:
            self.initial_path = self.dest_dir

        dest_dir = QFileDialog.getExistingDirectory(
            caption="Selecionar pasta de destino para as fotos",
            directory=self.initial_path,
            options=QFileDialog.Option.HideNameFilterDetails,
        )

        if dest_dir:
            if dest_dir == self.source_dir:
                self.dest_bool = False
                self.dest_dir = ""
                self.dest_dir_line_edit.setText(
                    "Atenção: pasta de destino igual à pasta das fotos"
                )
                self.dest_dir_line_edit.setStyleSheet("color: red;")
            elif dest_dir == self.folder_dir:
                self.dest_bool = False
                self.dest_dir = ""
                self.dest_dir_line_edit.setText(
                    "Atenção: pasta de destino igual à pasta da lista das fotos"
                )
                self.dest_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.dest_bool = True
                self.dest_dir = dest_dir
                self.dest_dir_line_edit.setText(dest_dir)
                self.dest_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = dest_dir
        elif not self.dest_dir:
            self.dest_bool = False
            self.dest_dir_line_edit.setText("Pasta não selecionada")

    def content_changed(self) -> None:
        """
        Checks if the content of the widgets is valid to enable the next button
        """
        if self.folder_dir and self.source_dir and self.dest_dir:
            self.next_button.setEnabled(True)
        else:
            self.next_button.setEnabled(False)

    def back(self) -> None:
        """
        Goes to the previous window
        """
        self.main_window.show()
        self.close()

    def next(self) -> None:
        """
        Goes to the next window
        """
        if not self.folder_dir or not self.source_dir or not self.dest_dir:
            return
        else:
            self.settings.setValue("folder_dir", self.folder_dir)
            self.settings.setValue("source_dir", self.source_dir)
            self.settings.setValue("dest_dir", self.dest_dir)

        # Check if dest_dir is empty
        if os.listdir(self.dest_dir):
            dialog = DeleteFolderDialog(self.dest_dir)
            dialog.exec()
            if not dialog.user_choice:
                # User chose not to delete contents or canceled or there was an error
                return

        self.next_window.show()
        self.close()
        self.next_window.start_folder_copy_process(
            self.folder_dir,
            self.source_dir,
            self.dest_dir,
        )


class CopyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(600, 250)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setEnabled(False)
        layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.done_button = MyPushButton("Fechar")
        self.done_button.setEnabled(False)
        self.done_button.clicked.connect(self.close)
        done_layout = QHBoxLayout()
        done_layout.addWidget(self.done_button)
        done_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(done_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def close(self) -> bool:
        """
        Closes the window
        """
        if hasattr(self, "copy_thread"):
            self.copy_thread.terminate()
        return super().close()

    def update_progress(self, value: int) -> None:
        """
        Update the progress bar value
        """
        self.progress_bar.setValue(value)

    def update_log(self, message: str) -> None:
        """
        Append log messages to the log area
        """
        self.log_area.append(message)

    def copy_finished(self, outcome: CopyOutcome) -> None:
        """
        Update the UI when copying is finished
        """
        match outcome:
            case CopyOutcome.SUCCESS:
                self.update_log(
                    "\n<span style='color: green; font-weight: bold;'>Cópia concluída com sucesso!</span>"
                )
            case CopyOutcome.FINISH_ERRORS:
                self.update_log(
                    "\n<span style='color: goldenrod; font-weight: bold;'>Cópia concluída com alguns erros!</span>"
                )
            case CopyOutcome.FAILURE:
                self.update_log(
                    "\n<span style='color: red; font-weight: bold;'>Cópia falhou!</span>"
                )

        self.done_button.setEnabled(True)

    def start_file_copy_process(
        self,
        file_path: str,
        source_dir: str,
        photos_ext: str,
        photos_format: str,
        dest_dir: str,
    ) -> None:
        """
        Starts the copy process
        """
        self.__format_exists: bool = bool(photos_format)
        self.update_log(f"A ler ficheiro {os.path.basename(file_path)}...")
        try:
            photos = self.read_file(file_path)
        except Exception as e:
            self.update_log(str(e))
            self.copy_finished(CopyOutcome.FAILURE)
        else:
            self.update_log(
                "<span style='color: green;'>Ficheiro lido com sucesso!</span>"
            )
            self.update_log(f"\nA copiar {photos.total()} fotos...")

            # Initialize progress bar
            self.progress_bar.setEnabled(True)
            # self.progress_bar.setTextVisible(True)

            # Start the file copying process in a separate thread
            self.copy_thread = CopyThread(
                source_dir, dest_dir, photos, photos_ext, photos_format
            )
            self.copy_thread.progress.connect(self.update_progress)
            self.copy_thread.update_log.connect(self.update_log)
            self.copy_thread.finished.connect(self.copy_finished)
            self.copy_thread.start()

    def start_folder_copy_process(
        self,
        folder_dir: str,
        source_dir: str,
        dest_dir: str,
    ) -> None:
        """
        Starts the copy process
        """
        self.__format_exists = False
        self.update_log(f"A ler pasta {os.path.basename(folder_dir)}...")
        try:
            photos = self.read_folder(folder_dir)
        except Exception as e:
            self.update_log(str(e))
            self.copy_finished(CopyOutcome.FAILURE)
        else:
            self.update_log(
                "<span style='color: green;'>Pasta lida com sucesso!</span>"
            )
            self.update_log(f"\nA copiar {photos.total()} fotos...")

            # Initialize progress bar
            self.progress_bar.setEnabled(True)
            # self.progress_bar.setTextVisible(True)

            # Start the file copying process in a separate thread
            self.copy_thread = CopyThread(source_dir, dest_dir, photos)
            self.copy_thread.progress.connect(self.update_progress)
            self.copy_thread.update_log.connect(self.update_log)
            self.copy_thread.finished.connect(self.copy_finished)
            self.copy_thread.start()

    def read_file(self, file_path: str) -> Counter[str]:
        """
        Reads the file and returns a Counter with the photos names
        """
        try:
            if file_path.endswith(".txt"):
                return self.read_txt_file(file_path)
            elif file_path.endswith(".xls") or file_path.endswith(".xlsx"):
                return self.read_excel_file(file_path)
            else:
                raise Exception("Oops! Formato de ficheiro não suportado!")
        except Exception:
            raise

    def read_txt_file(self, file_path: str) -> Counter[str]:
        """
        Reads the TXT file and returns a list with the photos names
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                photos: list[str] = file.readlines()
        except FileNotFoundError:
            raise Exception("Ficheiro não existe!")
        except UnicodeDecodeError as e:
            raise Exception(f"Erro no conteúdo do ficheiro: {e}")
        except OSError as e:
            raise Exception(f"Erro ao ler ficheiro: {e}")

        return self.get_counter(photos)

    def read_excel_file(self, file_path: str) -> Counter[str]:
        """
        Reads the Excel file and returns a list with the photos names
        """
        try:
            df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
            # Get columns names
            columns: list[Any] = df.columns.to_list()
            photos: list[str] = []
            for col in columns:
                if isinstance(col, int):
                    photos.append(str(col))
                photos.extend(df[col].to_list())
        except FileNotFoundError:
            raise Exception("Ficheiro não existe!")
        except UnicodeDecodeError as e:
            raise Exception(f"Erro no conteúdo do ficheiro: {e}")
        except (OSError, Exception) as e:
            raise Exception(f"Erro ao ler ficheiro: {e}")

        return self.get_counter(photos)

    def read_folder(self, folder_path: str) -> Counter[str]:
        """
        Reads the folder and returns a Counter with the photos names
        """
        try:
            photos: list[str] = os.listdir(folder_path)
        except FileNotFoundError:
            raise Exception("Pasta não existe!")
        except PermissionError:
            raise Exception("Permissão negada para aceder à pasta!")
        except OSError as e:
            raise Exception(f"Erro ao ler pasta: {e}")

        return self.get_counter(photos)

    def get_counter(self, photos: list[str]) -> Counter[str]:
        """
        Returns a Counter with the photos names filtered
        1. Strip names
        2. Remove empty names
        3. If format is set, remove names that are not digits
        4. Return a Counter with the names
        """
        filtered_photos: list[str] = [p_strip for p in photos if (p_strip := p.strip())]

        if self.__format_exists:
            removed_photos: list[str] = []
            filtered_photos_copy: list[str] = filtered_photos.copy()
            filtered_photos.clear()
            for p in filtered_photos_copy:
                if not p.isdigit():
                    removed_photos.append(p)
                else:
                    filtered_photos.append(str(int(p)))  # Remove leading zeros
            if removed_photos:
                self.update_log(
                    f"<span style='color: goldenrod;'>Aviso: Foram removidos {len(removed_photos)} nomes inválidos (não numéricos)!</span>"
                )

        return Counter(filtered_photos)


def main() -> None:
    app = QApplication([])

    QCoreApplication.setOrganizationName("ChicoApps")
    QCoreApplication.setApplicationName("FotoCopy")
    QCoreApplication.setApplicationVersion(__version__)

    initWindow = InitWindow()
    initWindow.show()

    # choiceWindow = ChoiceWindow()
    # choiceWindow.show()

    # copyWindow = CopyWindow()
    # copyWindow.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
