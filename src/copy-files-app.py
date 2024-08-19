import os
from collections import Counter

from PyQt6.QtWidgets import QApplication, QFileDialog

VERSION = "0.2.1"


def get_file_path() -> str:
    """
    Returns the path of the file selected by the user
    """
    file_path, _ = QFileDialog.getOpenFileName(
        caption="Selecionar ficheiro com lista de fotos a copiar",
        filter="Documento de texto (*.txt)",
    )
    if not file_path:
        raise NotImplementedError("get_file_path", "Ficheiro não selecionado")
    return file_path


def read_file(file_path: str) -> Counter[str]:
    """
    Reads the file and returns a Counter with the photos names
    """
    try:
        with open(file_path, encoding="utf-8") as file:
            photos: list[str] = file.readlines()
    except FileNotFoundError:
        raise NotImplementedError("read_file", "Ficheiro não encontrado")
    except Exception as e:
        raise NotImplementedError("read_file", f"Erro ao ler ficheiro: {e}")

    counter: Counter[str] = Counter([p.strip() for p in photos])
    return counter


def get_output_dir() -> str:
    """
    Returns the path of the output directory selected by the user
    """
    output_dir = QFileDialog.getExistingDirectory(
        caption="Selecionar pasta de destino para as fotos",
        options=QFileDialog.Option.HideNameFilterDetails,
    )
    if not output_dir:
        raise NotImplementedError("get_output_dir", "Pasta de destino não selecionada")
    return output_dir


def get_photos_dir() -> str:
    """
    Returns the path of the photos directory selected by the user
    """
    photos_dir = QFileDialog.getExistingDirectory(
        caption="Selecionar pasta com as fotos",
        options=QFileDialog.Option.HideNameFilterDetails,
    )
    if not photos_dir:
        raise NotImplementedError(
            "get_photos_dir", "Pasta com as fotos não selecionada"
        )
    return photos_dir


def get_photos_extension() -> str:
    """
    Returns the extension of the photos
    """
    return ".txt"
    # return ".jpg"
    # return ".png"


def copy_photos(photos: Counter[str], photos_dir: str, output_dir: str) -> None:
    """
    Copies the photos from the photos directory to the output directory
    """
    extension: str = get_photos_extension()
    for photo in photos:
        for count in range(1, photos[photo] + 1):
            out_photo: str = photo
            if photos[photo] > 1:
                out_photo += f" ({count})"
            try:
                with (
                    open(os.path.join(photos_dir, photo + extension), "rb") as file,
                    open(
                        os.path.join(output_dir, out_photo + extension), "wb"
                    ) as output_file,
                ):
                    output_file.write(file.read())
            except Exception as e:
                raise NotImplementedError(
                    "copy_photos", f"Erro ao copiar foto {out_photo!r}: {e}"
                )


def main() -> None:
    app = QApplication([])
    try:
        file_path = get_file_path()
        print(f"{file_path = }")
        photos = read_file(file_path)
        print(f"{photos = }")
        output_dir = get_output_dir()
        print(f"{output_dir = }")
        photos_dir = get_photos_dir()
        print(f"{photos_dir = }")
        copy_photos(photos, photos_dir, output_dir)

        app.exit(0)
    except NotImplementedError as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
