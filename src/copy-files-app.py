import os
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

__version__ = "1.0.2"


def getSettings() -> QSettings:
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


class CopyOutcome(Enum):
    SUCCESS = 1
    FINISH_ERRORS = 2
    FAILURE = 3


class CopyThread(QThread):
    progress = pyqtSignal(int)
    error_log = pyqtSignal(str)
    finished = pyqtSignal(CopyOutcome)

    def __init__(
        self, source_dir: str, dest_dir: str, photos: Counter[str], photos_ext: str
    ) -> None:
        super().__init__()
        self.source_dir: str = source_dir
        self.dest_dir: str = dest_dir
        self.photos: Counter[str] = photos
        self.photos_ext: str = photos_ext

    def run(self) -> None:
        total_photos: int = self.photos.total()
        i: int = 0
        errors: bool = False
        for photo in sorted(self.photos, key=lambda x: int(x) if x.isdigit() else x):
            for k in range(1, self.photos[photo] + 1):
                out_photo: str = photo
                if self.photos[photo] > 1:
                    out_photo += f" ({k})"

                src_file = os.path.join(self.source_dir, photo + self.photos_ext)
                dest_file = os.path.join(self.dest_dir, out_photo + self.photos_ext)
                try:
                    shutil.copyfile(src_file, dest_file)
                    i += 1
                except FileNotFoundError:
                    k_missing: int = self.photos[photo] + 1 - k
                    self.error_log.emit(
                        f"<span style='color: red;'>Ficheiro {photo + self.photos_ext!r} não encontrado (não foram copiadas {k_missing} fotos)!</span>"
                    )
                    errors = True
                    i += k_missing
                    break
                except OSError as e:
                    self.error_log.emit(
                        f"<span style='color: goldenrod;'>Erro ao copiar foto {photo + self.photos_ext!r}: {e}</span>"
                    )
                    errors = True
                finally:
                    # Emit progress signal
                    self.progress.emit(int((i + 1) / total_photos * 100))

        if errors:
            self.finished.emit(CopyOutcome.FINISH_ERRORS)
        else:
            self.finished.emit(CopyOutcome.SUCCESS)


class MyLabel(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setWordWrap(True)
        # Increase font size
        font = self.font()
        font.setPointSize(12)
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


class InitWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(400, 250)

        self.next_window = ChoiceWindow()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(0)

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
        layout.addStretch(0)

        self.next_button = MyPushButton("Começar")
        self.next_button.clicked.connect(self.next)
        layout.addWidget(self.next_button)
        layout.addStretch(0)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def next(self) -> None:
        """
        Goes to the next window
        """
        self.close()
        self.next_window.show()


class ChoiceWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(QCoreApplication.applicationName())
        self.setFixedSize(600, 450)

        self.next_window = CopyWindow()
        self.settings = getSettings()
        self.file_path: str = self.settings.value("file_path", "", type=str)
        self.source_dir: str = self.settings.value("source_dir", "", type=str)
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
        self.photos_ext_edit = MyLineEdit("", readOnly=False)
        self.photos_ext_edit.setMinimumWidth(75)
        self.photos_ext_edit.hide()
        photos_ext_layout = QHBoxLayout()
        photos_ext_layout.addWidget(self.photos_ext_label)
        photos_ext_layout.addWidget(self.photos_ext_combo)
        photos_ext_layout.addWidget(self.photos_ext_edit)
        photos_ext_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        photos_ext_layout.setContentsMargins(0, 0, 0, 10)
        layout.addLayout(photos_ext_layout)

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

        # NEXT
        self.next_button = MyPushButton("Próximo")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next)
        next_layout = QHBoxLayout()
        next_layout.addWidget(self.next_button)
        next_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        next_layout.setContentsMargins(0, 0, 0, 10)
        layout.addLayout(next_layout)

        # Set previous paths
        if self.file_path:
            self.file_line_edit.setText(self.file_path)
        if self.source_dir:
            self.source_dir_line_edit.setText(self.source_dir)
        if self.dest_dir:
            self.dest_dir_line_edit.setText(self.dest_dir)

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
            self.file_path = file_path
            self.file_line_edit.setText(file_path)
            self.initial_path = os.path.dirname(file_path)
        elif not self.file_path:
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
                self.source_dir = ""
                self.source_dir_line_edit.setText(
                    "Atenção: pasta de destino igual à pasta das fotos"
                )
                self.source_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.source_dir = source_dir
                self.source_dir_line_edit.setText(source_dir)
                self.source_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = source_dir
        elif not self.source_dir:
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
                self.dest_dir = ""
                self.dest_dir_line_edit.setText(
                    "Atenção: pasta de destino igual à pasta das fotos"
                )
                self.dest_dir_line_edit.setStyleSheet("color: red;")
            else:
                self.dest_dir = dest_dir
                self.dest_dir_line_edit.setText(dest_dir)
                self.dest_dir_line_edit.setStyleSheet("color: black;")
                self.initial_path = dest_dir
        elif not self.dest_dir:
            self.dest_dir_line_edit.setText("Pasta não selecionada")

    def content_changed(self) -> None:
        """
        Checks if the content of the widgets has changed
        """
        if (
            hasattr(self, "file_path")
            and hasattr(self, "source_dir")
            and hasattr(self, "dest_dir")
        ):
            self.next_button.setEnabled(True)
        else:
            self.next_button.setEnabled(False)

    def on_ext_combo_change(self, index: int) -> None:
        """
        Shows or hides the line edit for custom photo extension
        """
        if self.photos_ext_combo.currentText() == "Outra...":
            self.photos_ext_edit.show()
            self.photos_ext_edit.setFocus()
        else:
            self.photos_ext_edit.hide()
            self.photos_ext_edit.setText("")

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

        self.photos_ext: str = self.photos_ext_combo.currentText()
        if self.photos_ext == "Outra...":
            self.photos_ext = self.photos_ext_edit.text().strip()
            if not self.photos_ext.startswith("."):
                self.photos_ext = "." + self.photos_ext
            if len(self.photos_ext) < 2:
                self.photos_ext = ".jpg"  # Default extension

        self.close()
        self.next_window.show()
        self.next_window.start_copy_process(
            self.file_path, self.source_dir, self.photos_ext, self.dest_dir
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
                    "<span style='color: green; font-weight: bold;'>Cópia concluída com sucesso!</span>"
                )
            case CopyOutcome.FINISH_ERRORS:
                self.update_log(
                    "<span style='color: goldenrod; font-weight: bold;'>Cópia concluída com alguns erros!</span>"
                )
            case CopyOutcome.FAILURE:
                self.update_log(
                    "<span style='color: red; font-weight: bold;'>Cópia falhou!</span>"
                )

        self.done_button.setEnabled(True)

    def start_copy_process(
        self, file_path: str, source_dir: str, photos_ext: str, dest_dir: str
    ) -> None:
        """
        Starts the copy process
        """
        self.update_log("A ler ficheiro...")
        try:
            photos = self.read_file(file_path)
        except Exception as e:
            self.update_log(str(e))
            self.copy_finished(CopyOutcome.FAILURE)
        else:
            self.update_log(
                "<span style='color: green;'>Ficheiro lido com sucesso!</span>"
            )
            self.update_log(f"A copiar {photos.total()} fotos...")

            # Initialize progress bar
            self.progress_bar.setEnabled(True)
            # self.progress_bar.setTextVisible(True)

            # Start the file copying process in a separate thread
            self.copy_thread = CopyThread(source_dir, dest_dir, photos, photos_ext)
            self.copy_thread.progress.connect(self.update_progress)
            self.copy_thread.error_log.connect(self.update_log)
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

        return Counter([p_filtered for p in photos if (p_filtered := p.strip())])

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

        return Counter([p_filtered for p in photos if (p_filtered := p.strip())])


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
