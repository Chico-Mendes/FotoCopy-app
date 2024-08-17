import os
from tkinter import filedialog, Tk


def get_file_path() -> str:
    """
    Returns the path of the file selected by the user
    """
    file_path = filedialog.askopenfilename(
        defaultextension=".txt",
        filetypes=[("Documento de texto", "*.txt")],
        title="Selecionar ficheiro com lista de fotos a copiar",
    )
    if not file_path:
        raise NotImplementedError("get_file_path", "Ficheiro não selecionado")
    return file_path


def read_file(file_path: str) -> list[str]:
    """
    Returns a list of photo names from the file
    """
    try:
        with open(file_path, "rt", encoding="utf-8") as file:
            photos = file.readlines()
    except FileNotFoundError:
        raise NotImplementedError("read_file", "Ficheiro não encontrado")
    except Exception as e:
        raise NotImplementedError("read_file", f"Erro ao ler ficheiro: {e}")
    return photos


def get_output_dir() -> str:
    """
    Returns the path of the output directory selected by the user
    """
    output_dir = filedialog.askdirectory(
        title="Selecionar pasta de destino para as fotos",
    )
    if not output_dir:
        raise NotImplementedError("get_output_dir", "Pasta de destino não selecionada")
    return output_dir


def get_photos_dir() -> str:
    """
    Returns the path of the photos directory selected by the user
    """
    photos_dir = filedialog.askdirectory(
        title="Selecionar pasta com as fotos",
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
    # return ".txt"
    # return ".jpg"
    return ".png"


def copy_photos(file_path: str, photos_dir: str, output_dir: str) -> None:
    """
    Copies the photos from the list to the output directory
    """
    photos = read_file(file_path)
    print(f"{photos = }")
    extension = get_photos_extension()
    for photo in photos:
        photo = photo.strip()
        try:
            with open(os.path.join(photos_dir, photo + extension), "rb") as file:
                with open(
                    os.path.join(output_dir, photo + extension), "wb"
                ) as output_file:
                    output_file.write(file.read())
        except Exception as e:
            raise NotImplementedError(
                "copy_photos", f"Erro ao copiar foto {photo}: {e}"
            )


def main() -> None:
    try:
        file_path = get_file_path()
        print(f"{file_path = }")
        # photos = read_file(file_path)
        # print(f"{photos = }")
        output_dir = get_output_dir()
        print(f"{output_dir = }")
        photos_dir = get_photos_dir()
        print(f"{photos_dir = }")
        copy_photos(file_path, photos_dir, output_dir)
    except NotImplementedError as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    main()
